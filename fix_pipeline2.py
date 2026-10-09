import re

with open('pipeline.py', 'r', encoding='utf-8') as f:
    text = f.read()

target = r"    clips_per_chunk = max\(3, int\(max_clips / len\(chunks\)\) \+ 1\).*?Encuentra hasta \{clips_per_chunk\} clips DIVERTIDOS o BUENOS basandote en el prompt\."

replacement = r'''    if max_clips == 0:
        clips_instruction = "Encuentra TODOS los clips DIVERTIDOS o BUENOS que valgan la pena en este bloque (no hay limite, extrae todo lo bueno)"
    else:
        clips_per_chunk = max(3, int(max_clips / len(chunks)) + 1)
        clips_instruction = f"Encuentra hasta {clips_per_chunk} clips DIVERTIDOS o BUENOS"
    
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
            
        if progress_callback: progress_callback(70 + int(20 * (chunk_idx / len(chunks))), f"Analizando bloque {chunk_idx+1}/{len(chunks)} con Gemini 2.5 Flash...")
        
        sys_prompt = f"Eres Leito4Gaming, un streamer y creador de videos virales de gaming de Argentina. Estas creando metadatos para tus propios clips, de juegos que TU MISMO jugaste (NOMBRE DEL JUEGO: {video_basename}). CRITICO: Escribe SIEMPRE en Español Argentino autentico (rioplatense). NO uses español neutro. NUNCA uses la palabra o conjugaciones de 'tu'. Habla siempre tratando de VOS. Usa modismos locales ('cagazo', 'la puta madre'). EVITA 'che' y NUNCA uses 'boludo'. NUNCA asumas que no jugaste el juego. Escribe como un gamer con actitud, en PRIMERA PERSONA. Recibes el AUDIO EXACTO y la transcripcion de una seccion de {CHUNK_DUR/60} minutos. Usa el AUDIO para distinguir cuando estas leyendo dialogos del juego de cuando estas reaccionando espontaneamente, hablando a tu chat o gritando de un susto. PRIORIZA LAS REACCIONES REALES, CHISTES Y SUSTOS. {clips_instruction} basandote en el prompt.'''

new_text = re.sub(target, replacement, text, flags=re.DOTALL)
if new_text != text:
    with open('pipeline.py', 'w', encoding='utf-8') as f:
        f.write(new_text)
    print("Replaced!")
else:
    print("Not replaced.")
