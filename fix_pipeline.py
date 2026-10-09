import re, json

with open('pipeline.py', 'r', encoding='utf-8') as f:
    text = f.read()

target = r"    if os.path.exists\(transcript_file\):.*?        if progress_callback: progress_callback\(70 \+ int\(20 \* \(chunk_idx / len\(chunks\)\)\), f\"Analizando bloque \{chunk_idx\+1\}/\{len\(chunks\)\} con Gemini 2.5 Flash...\"\)"

replacement = r'''    temp_wav = os.path.join(temp_dir, f"{video_basename}_full.wav")
    if not os.path.exists(temp_wav):
        if progress_callback: progress_callback(10, "Extrayendo audio general...")
        subprocess.run([
            "ffmpeg", "-i", video_path,
            "-vn", "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le",
            "-y", temp_wav
        ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
    if os.path.exists(transcript_file):
        if progress_callback: progress_callback(10, "Cargando transcripcion previa de la cache...")
        print("Cargando transcripcion cacheada...")
        with open(transcript_file, "r", encoding="utf-8") as f:
            transcript_segments = json.load(f)
    else:
        if progress_callback: progress_callback(30, "Transcribiendo audio con Whisper (Esto puede tardar)...")
        print("Cargando modelo Whisper...")
        model = whisper.load_model("small")
        print("Transcribiendo...")
        result = model.transcribe(temp_wav, word_timestamps=False, verbose=True)
        transcript_segments = result["segments"]
        
        with open(transcript_file, "w", encoding="utf-8") as f:
            json.dump(transcript_segments, f, indent=4, ensure_ascii=False)
            
    # Formatear transcripcion para Gemini
    if progress_callback: progress_callback(70, "Analizando contexto con Gemini 2.5 Flash...")
    
    CHUNK_DUR = 1800 # 30 minutes per chunk
    chunks = []
    current_chunk_text = ""
    current_chunk_start = 0.0
    current_chunk_end = 0.0
    
    for seg in transcript_segments:
        start = seg['start']
        end = seg['end']
        is_excluded = False
        if exclusion_zones:
            for ez_start, ez_end in exclusion_zones:
                if max(start, ez_start) < min(end, ez_end):
                    is_excluded = True
                    break
        if not is_excluded:
            if not current_chunk_text:
                current_chunk_start = start
            if start - current_chunk_start > CHUNK_DUR:
                chunks.append({"start": current_chunk_start, "end": current_chunk_end, "text": current_chunk_text})
                current_chunk_text = ""
                current_chunk_start = start
            current_chunk_text += f"[{seg['start']:.1f} - {seg['end']:.1f}] {seg['text']}\\n"
            current_chunk_end = end
            
    if current_chunk_text.strip():
        chunks.append({"start": current_chunk_start, "end": current_chunk_end, "text": current_chunk_text})
        
    if not chunks:
        print("Todo el texto esta excluido por clips anteriores. No hay nada nuevo que analizar.")
        return [], 0, 0
        
    link_instruction = "que SIEMPRE termine con 'Podes ver el video completo haciendo click en el link' seguida de los " if "gourmet" in video_path.lower() else ""
    
    total_input_tokens = 0
    total_output_tokens = 0
    final_clips = []
    
    clips_per_chunk = max(3, int(max_clips / len(chunks)) + 1)
    
    import time
    for chunk_idx, chunk_data in enumerate(chunks):
        chunk_start = chunk_data["start"]
        chunk_end = chunk_data["end"]
        chunk_text = chunk_data["text"]
        
        if progress_callback: progress_callback(70 + int(20 * (chunk_idx / len(chunks))), f"Preparando audio del bloque {chunk_idx+1}/{len(chunks)}...")
        
        # Cortar audio del chunk
        chunk_mp3_path = os.path.join(temp_dir, f"chunk_{chunk_idx}.mp3")
        subprocess.run([
            "ffmpeg", "-y", "-ss", str(chunk_start), "-to", str(chunk_end),
            "-i", temp_wav, "-c:a", "libmp3lame", "-q:a", "5",
            chunk_mp3_path
        ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        if progress_callback: progress_callback(70 + int(20 * (chunk_idx / len(chunks))), f"Subiendo audio {chunk_idx+1}/{len(chunks)} a Gemini...")
        g_audio = client.files.upload(file=chunk_mp3_path)
        while g_audio.state and "PROCESSING" in str(g_audio.state):
            time.sleep(2)
            g_audio = client.files.get(name=g_audio.name)
            
        if progress_callback: progress_callback(70 + int(20 * (chunk_idx / len(chunks))), f"Analizando bloque {chunk_idx+1}/{len(chunks)} con Gemini 2.5 Flash...")'''

new_text = re.sub(target, replacement, text, flags=re.DOTALL)
if new_text != text:
    with open('pipeline.py', 'w', encoding='utf-8') as f:
        f.write(new_text)
    print("Replaced!")
else:
    print("Not replaced.")
