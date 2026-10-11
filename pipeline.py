import os
import subprocess
import numpy as np
import cv2
import json
import uuid
import time
import re
import PIL.Image
import wave

def get_feedback_injection() -> str:
    fb_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "db", "feedback_ia.json")
    if not os.path.exists(fb_file):
        return ""
    try:
        with open(fb_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        positives = [d for d in data if d.get("feedback") == "up" and str(d.get("transcript", "")).strip()]
        negatives = [d for d in data if d.get("feedback") == "down" and str(d.get("transcript", "")).strip()]
        
        import random
        pos_sample = random.sample(positives, min(3, len(positives)))
        neg_sample = random.sample(negatives, min(3, len(negatives)))
        
        if not pos_sample and not neg_sample:
            return ""
            
        inj = "\n\n--- INYECCIÓN DE APRENDIZAJE (FEEDBACK HISTÓRICO DEL USUARIO) ---\n"
        inj += "Aprende de estos ejemplos pasados que el usuario ha calificado manualmente:\n"
        if pos_sample:
            inj += "\nEjemplos que al usuario LE GUSTARON (Objetivos a buscar):\n"
            for i, p in enumerate(pos_sample):
                inj += f"[BUENO {i+1}] Transcripción: \"{p.get('transcript')}\"\n"
        
        if neg_sample:
            inj += "\nEjemplos que al usuario NO LE GUSTARON (Falsos positivos a EVITAR. Especialmente charlas aburridas, saludos o menús sin chiste ni susto):\n"
            for i, n in enumerate(neg_sample):
                inj += f"[MALO {i+1}] Transcripción: \"{n.get('transcript')}\"\n"
        
        inj += "-------------------------------------------------------------------\n"
        return inj
    except Exception as e:
        print(f"Error loading feedback: {e}")
        return ""


def analyze_video_local_first(video_path, prompt, api_key, temp_dir, progress_callback=None, exclusion_zones=None, incremental_save_cb=None, max_clips=15):
    try:
        from google import genai
    except ImportError:
        raise Exception("La librería google-genai no está instalada.")
        
    client = genai.Client(api_key=api_key.strip())
    
    video_basename = os.path.basename(video_path)
    
    if progress_callback: progress_callback(10, "Extrayendo audio general...")
    
    # Hash sencillo basado en nombre para reutilizar audio si es el mismo video
    safe_name = "".join(c for c in video_basename if c.isalnum() or c in " _-")
    temp_wav = os.path.join(temp_dir, f"{safe_name}_audio_temp.wav")
    
    if os.path.exists(temp_wav) and os.path.getsize(temp_wav) > 1000:
        print("Audio general ya extraído, utilizando caché...")
    else:
        print("Extrayendo audio para análisis RMS...")
        subprocess.run([
            "ffmpeg", "-i", video_path,
            "-vn", "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le",
            "-y", temp_wav
        ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
    if progress_callback: progress_callback(20, "Calculando mapa de volumen (RMS)...")
    print("Analizando picos de volumen...")
    with wave.open(temp_wav, "rb") as wf:
        framerate = wf.getframerate()
        n_frames = wf.getnframes()
        audio_data = np.frombuffer(wf.readframes(n_frames), dtype=np.int16).astype(np.float64)

    chunk_samples = 16000 
    rms_values = []
    for i in range(0, len(audio_data), chunk_samples):
        chunk = audio_data[i:i+chunk_samples]
        rms = np.sqrt(np.mean(chunk**2))
        rms_values.append(rms)
        
    rms_array = np.array(rms_values)
    
    # === IGNORAR ZONAS YA PROCESADAS ===
    if exclusion_zones:
        if progress_callback: progress_callback(25, "Filtrando fragmentos ya procesados...")
        for ex_start, ex_end in exclusion_zones:
            # Añadir 15 segundos de margen a cada lado para no capturar el borde
            s_idx = max(0, int(ex_start) - 15)
            e_idx = min(len(rms_array), int(ex_end) + 15)
            rms_array[s_idx:e_idx] = 0.0
            
    # Solo calcular el umbral con los valores que NO son cero
    nonzero_rms = rms_array[rms_array > 0]
    if len(nonzero_rms) > 0:
        threshold = np.percentile(nonzero_rms, 90) 
    else:
        threshold = 999999.0

    
    loud_seconds = np.where(rms_array > threshold)[0]
    
    segments = []
    current_segment = []
    for s in loud_seconds:
        if not current_segment:
            current_segment = [s]
        else:
            if s - current_segment[-1] <= 5:
                current_segment.append(s)
            else:
                segments.append((current_segment[0], current_segment[-1]))
                current_segment = [s]
    if current_segment:
        segments.append((current_segment[0], current_segment[-1]))
        
    valid_segments = []
    for start, end in segments:
        start, end = start, end + 1
        length = end - start
        if length < 5: continue
        
        pad_before = 45 # 45 segundos de contexto previo para que entienda el chiste
        pad_after = 25  # 25 segundos después
        
        start = max(0, start - pad_before)
        end = end + pad_after
            
        if end - start > 120:
            end = start + 120
            
        valid_segments.append((start, end))
        
    print(f"Se detectaron {len(valid_segments)} picos de interés.")
    
    valid_segments_filtered = []
    for start, end in valid_segments:
        is_excluded = False
        if exclusion_zones:
            for ez_start, ez_end in exclusion_zones:
                if max(start, ez_start) < min(end, ez_end):
                    is_excluded = True
                    break
        if not is_excluded:
            valid_segments_filtered.append((start, end))
            
    print(f"Tras aplicar filtros de tiempo quedan {len(valid_segments_filtered)} picos.")
    
    if len(valid_segments_filtered) > 0:
        valid_segments_filtered.sort(key=lambda seg: np.max(rms_array[seg[0]:seg[1]]), reverse=True)
        limit = max_clips if max_clips > 0 else 30
        valid_segments_filtered = valid_segments_filtered[:limit] # Limitar a los mas fuertes
        valid_segments_filtered.sort(key=lambda x: x[0])
        
    valid_segments = valid_segments_filtered
    print(f"Tras aplicar zonas de exclusión (clips previos/actuales), quedan {len(valid_segments)} segmentos a evaluar.")
    
    if len(valid_segments) == 0:
        return [], 0, 0
        
    total_input_tokens = 0
    total_output_tokens = 0
    
    link_instruction = "que SIEMPRE termine con 'Podes ver el video completo haciendo click en el link' seguida de los " if "gourmet" in video_path.lower() else ""
    sys_prompt = f"Eres Leito4Gaming, un streamer y creador de videos virales de gaming de Argentina. Estás creando metadatos para tus propios clips, de juegos que TÚ MISMO jugaste (NOMBRE DEL JUEGO: {video_basename}). CRÍTICO: Escribe SIEMPRE en Español Argentino auténtico (rioplatense). NO uses español neutro. NUNCA uses la palabra o conjugaciones de 'tú' (ej: nunca digas 'Te ha pasado', debes decir 'Te pasó', 'Mirá', 'Fijate'). Habla siempre tratando de VOS. Usa modismos locales ('cagazo', 'la puta madre'). EVITA 'che' y NUNCA uses 'boludo'. NUNCA asumas que no jugaste el juego ('Me contaron'). Escribe como un gamer con actitud, en PRIMERA PERSONA. Recibes el audio y fotogramas. Evalúa si es BUENO o DIVERTIDO según el prompt. Si es silencio, responde 'RECHAZADO'. Si tiene valor, devuelve JSON: 'start' (float, inicio, sumale offset), 'end' (float, fin, sumale offset), 'category' (string: 'susto' si es miedo/grito/terror, 'streamer' si es charla/anécdota/explicación/lore, 'humor' si es chiste/broma/fail, 'gameplay' si es jugada/combate/boss/muerte épica), 'reason' (string), 'virality_score' (int 70-99), 'transcript' (string), 'social_title' (string, Titulo ingenioso y directo que resuma EXACTAMENTE lo que pasa o se dice en el clip), 'social_desc' (string, descripcion MUY CORTA de APENAS UN RENGLON (max 10 palabras) que tenga sentido con el clip, en PRIMERA PERSONA. {link_instruction} Luego pon solo 3 hashtags populares del juego), 'yt_title' (string, llamativo para YT Shorts), 'yt_desc' (string, descripción CORTA), 'yt_tags' (string, separadas por coma, incluye 'Leito4Gaming' y 'Leito4GamingPlus' y tags del juego real). IMPORTANTE: Clip entre 35 y 75 segundos. DEBES RETROCEDER LO SUFICIENTE para incluir TODO el contexto previo necesario (la preparación del chiste o susto). No cortes las oraciones a la mitad. FUNDAMENTAL: Los títulos y descripciones DEBEN referirse ESTRICTAMENTE a lo que se dice o pasa en el clip. Usa frases de tu propio diálogo en la descripción para que no suene genérico."
    sys_prompt += get_feedback_injection()
    
    final_clips = []
    
    for idx, (start, end) in enumerate(valid_segments):
        base_percent = 30 + int(60 * (idx / len(valid_segments)))
        if progress_callback: progress_callback(base_percent, f"Extrayendo mini-clip {idx+1}/{len(valid_segments)}...")
        print(f"--> Extrayendo video y fotogramas clave del segmento: {start}s - {end}s")
        temp_clip = os.path.join(temp_dir, f"temp_clip_{idx}.mp4")
        temp_audio_clip = os.path.join(temp_dir, f"temp_audio_{idx}.mp3")
        
        duration = end - start
        subprocess.run([
            "ffmpeg", "-ss", str(start), "-i", video_path, "-t", str(duration),
            "-c:v", "libx264", "-preset", "ultrafast", "-crf", "35",
            "-c:a", "libmp3lame", "-b:a", "64k",
            "-y", temp_clip
        ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        subprocess.run([
            "ffmpeg", "-i", temp_clip, "-vn", "-c:a", "copy", "-y", temp_audio_clip
        ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        cap = cv2.VideoCapture(temp_clip)
        frames_extracted = []
        prev_hist = None
        fps = cap.get(cv2.CAP_PROP_FPS)
        if fps == 0: fps = 30
        
        frame_count = 0
        while True:
            ret, frame = cap.read()
            if not ret: break
            
            if frame_count % int(fps) == 0:
                frame_resized = cv2.resize(frame, (512, 512))
                
                hist = cv2.calcHist([frame_resized], [0, 1, 2], None, [8, 8, 8], [0, 256, 0, 256, 0, 256])
                hist = cv2.normalize(hist, hist).flatten()
                
                save_frame = False
                if prev_hist is None:
                    save_frame = True
                else:
                    dist = cv2.compareHist(prev_hist, hist, cv2.HISTCMP_CORREL)
                    if dist < 0.8:
                        save_frame = True
                
                if save_frame:
                    prev_hist = hist
                    frames_extracted.append(PIL.Image.fromarray(cv2.cvtColor(frame_resized, cv2.COLOR_BGR2RGB)))
                    
            frame_count += 1
            
        cap.release()
        
        if progress_callback: progress_callback(base_percent + 2, f"Subiendo mini-audio {idx+1} a la IA...")
        print(f"Subiendo mini-audio {idx} a Gemini API...")
        g_audio = client.files.upload(file=temp_audio_clip)
        wait_time = 0
        while g_audio.state and "PROCESSING" in str(g_audio.state):
            if wait_time > 300: # 5 minutos maximo
                raise Exception("El servidor de Gemini se quedo colgado procesando el video (TimeOut).")
            time.sleep(5)
            wait_time += 5
            g_audio = client.files.get(name=g_audio.name)
            
        if g_audio.state and "FAILED" in str(g_audio.state):
            raise Exception("Gemini rechazo el archivo de video/audio (FAILED).")
            
        if progress_callback: progress_callback(base_percent + 4, f"Evaluando clip {idx+1}/{len(valid_segments)} con Gemini 2.5 Flash...")
        print(f"Evaluando clip {idx} con Gemini 2.5 Flash...")
        
        prompt_text = f"OFFSET ORIGINAL: Este clip empieza en el segundo {start} del video original. Tienes que devolver tu 'start' entre {start} y {end}.\n\nPROMPT DEL USUARIO: {prompt}"
        
        response = None
        for attempt in range(4):
            try:
                import concurrent.futures
                
                def call_api1():
                    return client.models.generate_content(
                        model='gemini-2.5-flash',
                        contents=[g_audio] + frames_extracted + [sys_prompt, prompt_text],
                        config={
                            "temperature": 0.3,
                            "safety_settings": [
                                {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
                                {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
                                {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
                                {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
                            ],
                            "response_mime_type": "application/json",
                        }
                    )
                
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(call_api1)
                    try:
                        response = future.result(timeout=300)
                    except concurrent.futures.TimeoutError:
                        raise Exception("Gemini API timeout")
                break
            except Exception as e:
                err_str = str(e)
                if "limit: 0" in err_str:
                    raise Exception("QUOTA_AGOTADA: Has superado el límite gratuito diario o Google aún no procesa tu prepago. Debes esperar.")
                if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str:
                    if progress_callback: progress_callback(base_percent + 4, f"Límite API alcanzado. Pausando 45s...")
                    print(f"Límite de API alcanzado (429). Esperando 45 segundos... (Intento {attempt+1})")
                    time.sleep(45)
                else:
                    print(f"Error evaluando clip {idx}: {e}")
                    break
        
        if response is None:
            print(f"Omitiendo clip {idx} debido a errores continuos de API.")
        else:
            try:
                if hasattr(response, 'usage_metadata') and response.usage_metadata:
                    total_input_tokens += getattr(response.usage_metadata, 'prompt_token_count', 0)
                    total_output_tokens += getattr(response.usage_metadata, 'candidates_token_count', 0)
                
                txt = response.text
                if txt and "RECHAZADO" not in txt:
                    match = re.search(r'\{.*\}', txt, re.DOTALL)
                    if match:
                        c = json.loads(match.group(0))
                        if c.get('start', 0) < start:
                            c['start'] += start
                            c['end'] += start
                        
                        # Garantizar longitud mínima de 35s
                        c_start = c.get('start', 0)
                        c_end = c.get('end', 0)
                        if (c_end - c_start) < 35:
                            diff = 35 - (c_end - c_start)
                            c['start'] = max(0, c_start - (diff / 2))
                            c['end'] = c_end + (diff / 2)
                            
                        c["id"] = "ai_" + str(uuid.uuid4())[:4]
                        final_clips.append(c)
                        if incremental_save_cb: incremental_save_cb(c)
                        print(f"¡Clip Aprobado! {c.get('reason')} - Duración final: {c['end'] - c['start']}s")
                    else:
                        print(f"Rechazado o formato inválido: {txt}")
                else:
                    print("Clip RECHAZADO por la IA.")
            except Exception as e:
                print(f"Error procesando la respuesta del clip {idx}: {e}")
            
        try:
            os.remove(temp_clip)
            os.remove(temp_audio_clip)
            client.files.delete(name=g_audio.name)
        except:
            pass

    return final_clips, total_input_tokens, total_output_tokens


def analyze_video_semantic(video_path, prompt, api_key, temp_dir, progress_callback=None, exclusion_zones=None, incremental_save_cb=None, max_clips=15, keywords=''):
    try:
        from google import genai
        import whisper
    except ImportError as e:
        raise Exception(f"Falta una librerÃ­a requerida: {e}")
        
    client = genai.Client(api_key=api_key.strip())
    video_basename = os.path.basename(video_path)
    
    # Directorio de caché para transcripciones
    db_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "db")
    os.makedirs(db_dir, exist_ok=True)
    transcript_file = os.path.join(db_dir, f"{video_basename}_transcript.json")
    
    temp_wav = os.path.join(temp_dir, f"{video_basename}_full.wav")
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
            current_chunk_text += f"[{seg['start']:.1f} - {seg['end']:.1f}] {seg['text']}\n"
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
    
    if max_clips == 0:
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
        
        # Cortar audio y video (low fps) del chunk para contexto visual completo
        chunk_mp3_path = os.path.join(temp_dir, f"chunk_{chunk_idx}.mp4")
        subprocess.run([
            "ffmpeg", "-y", "-ss", str(chunk_start), "-to", str(chunk_end),
            "-i", video_path, "-r", "1", "-vf", "scale=480:-2", "-c:v", "libx264", "-preset", "ultrafast", "-crf", "35",
            "-c:a", "libmp3lame", "-q:a", "5",
            chunk_mp3_path
        ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        if progress_callback: progress_callback(70 + int(20 * (chunk_idx / len(chunks))), f"Subiendo audio {chunk_idx+1}/{len(chunks)} a Gemini...")
        g_audio = client.files.upload(file=chunk_mp3_path)
        wait_time = 0
        while g_audio.state and "PROCESSING" in str(g_audio.state):
            if wait_time > 300: # 5 minutos maximo
                raise Exception("El servidor de Gemini se quedo colgado procesando el video (TimeOut).")
            time.sleep(5)
            wait_time += 5
            g_audio = client.files.get(name=g_audio.name)
            
        if g_audio.state and "FAILED" in str(g_audio.state):
            raise Exception("Gemini rechazo el archivo de video/audio (FAILED).")
            
        if progress_callback: progress_callback(70 + int(20 * (chunk_idx / len(chunks))), f"Analizando bloque {chunk_idx+1}/{len(chunks)} con Gemini 2.5 Flash...")
        
        sys_prompt = f"Eres Leito4Gaming, un streamer y creador de videos virales de gaming de Argentina. Estas creando metadatos para tus propios clips, de juegos que TU MISMO jugaste (NOMBRE DEL JUEGO: {video_basename}). CRITICO: Escribe SIEMPRE en Español Argentino autentico (rioplatense). NO uses español neutro. NUNCA uses la palabra o conjugaciones de 'tu'. Habla siempre tratando de VOS. Usa modismos locales ('cagazo', 'la puta madre'). EVITA 'che' y NUNCA uses 'boludo'. NUNCA asumas que no jugaste el juego. Escribe como un gamer con actitud, en PRIMERA PERSONA. Recibes el VIDEO EXACTO (a 1 frame por segundo) y la transcripcion de una seccion de {CHUNK_DUR/60} minutos. Usa el VIDEO y el AUDIO para entender el contexto visual (ej: si murio en el juego, si hay un boss, sus expresiones faciales) y distinguir cuando esta leyendo dialogos del juego de cuando reacciona espontaneamente. PRIORIZA LAS REACCIONES REALES, CHISTES, SUSTOS Y MUERTES EPICAS. {clips_instruction} basandote en el prompt. IMPORTANTE: Clips entre 35 y 75 segundos. Asegurate de abarcar TODO el contexto (el inicio de la anecdota o explicacion) para que tenga sentido. Devuelve UNICAMENTE lista JSON valida. Formato: [{{\"start\": float, \"end\": float, \"category\": \"susto\"|\"streamer\"|\"humor\"|\"gameplay\", \"reason\": \"string corto\", \"virality_score\": int (70-99), \"transcript\": \"string\", \"social_title\": \"Titulo ingenioso y directo que resuma EXACTAMENTE lo que pasa o se dice en el clip\", \"social_desc\": \"Descripcion MUY CORTA de APENAS UN RENGLON (max 10 palabras) que tenga sentido con el clip, en PRIMERA PERSONA. {link_instruction} Luego pon solo 3 hashtags populares del juego\", \"yt_title\": \"Titulo super llamativo para YouTube Shorts\", \"yt_desc\": \"Descripcion CORTA en PRIMERA PERSONA\", \"yt_tags\": \"Etiquetas SIN hashtag\"}}]. Respeta estrictamente JSON. FUNDAMENTAL: EL AUDIO COMIENZA EN EL SEGUNDO {chunk_start}. Los tiempos 'start' y 'end' que devuelvas en el JSON deben ser RELATIVOS AL VIDEO ORIGINAL, es decir, usa exactamente las marcas de tiempo que aparecen en la transcripcion."
        sys_prompt += get_feedback_injection()
        
        prompt_text = f"PROMPT DEL USUARIO: {prompt}\n\nAqui tienes la transcripcion del bloque {chunk_idx+1} (El video que ves abarca exactamente este mismo tramo):\n\n{chunk_text}"
        
        try:
            response = None
            for attempt in range(4):
                try:
                    import concurrent.futures
                    
                    def call_api2():
                        return client.models.generate_content(
                            model='gemini-2.5-flash',
                            contents=[g_audio, sys_prompt, prompt_text],
                            config={
                                "temperature": 0.3,
                                "safety_settings": [
                                    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
                                    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
                                    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
                                    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
                                ],
                                "response_mime_type": "application/json",
                            }
                        )
                        
                    with concurrent.futures.ThreadPoolExecutor() as executor:
                        future = executor.submit(call_api2)
                        try:
                            response = future.result(timeout=300)
                        except concurrent.futures.TimeoutError:
                            raise Exception("Gemini API timeout")
                    break
                except Exception as e:
                    import time
                    err_str = str(e)
                    if "limit: 0" in err_str:
                        raise Exception("QUOTA_AGOTADA: Has superado el limite gratuito diario o Google aun no procesa tu prepago. Debes esperar.")
                    if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str:
                        if progress_callback: progress_callback(75, f"Limite API alcanzado. Pausando 45s...")
                        print(f"Limite de API alcanzado (429). Esperando 45 segundos... (Intento {attempt+1})")
                        time.sleep(45)
                    else:
                        raise e
                        
            if response is None:
                raise Exception("Limite de API excedido continuamente.")
                
            if hasattr(response, 'usage_metadata') and response.usage_metadata:
                total_input_tokens += getattr(response.usage_metadata, 'prompt_token_count', 0)
                total_output_tokens += getattr(response.usage_metadata, 'candidates_token_count', 0)
            
            txt = response.text
            match = re.search(r'\[.*\]', txt, re.DOTALL)
            if match:
                clips_list = json.loads(match.group(0))
                for c in clips_list:
                    # Validar exclusion zones
                    # Garantizar longitud mínima de 35s
                    start = c.get('start', 0)
                    end = c.get('end', 0)
                    if (end - start) < 35:
                        diff = 35 - (end - start)
                        c['start'] = max(0, start - (diff / 2))
                        c['end'] = end + (diff / 2)
                        start = c['start']
                        end = c['end']
                        
                    is_excluded = False
                    if exclusion_zones:
                        for ez_start, ez_end in exclusion_zones:
                            if ez_start <= start <= ez_end or ez_start <= end <= ez_end or start <= ez_start <= end:
                                is_excluded = True
                                break
                    if not is_excluded:
                        c["id"] = "ai_" + str(uuid.uuid4())[:4]
                        final_clips.append(c)
            else:
                if "RECHAZADO" in txt or len(txt) > 0:
                    print(f"Gemini no devolvió JSON: {txt}")
                    raise Exception(f"Gemini respondió pero no con clips JSON: {txt[:200]}...")
        except Exception as e:
            print(f"Error de Gemini: {e}")
            raise Exception(f"Error procesando la transcripción con la IA: {str(e)}")
            
        try:
            client.files.delete(name=g_audio.name)
            if os.path.exists(chunk_mp3_path):
                os.remove(chunk_mp3_path)
        except:
            pass
        
    if progress_callback: progress_callback(95, "Generando previsualizaciones...")
    
    # Extract temp videos for each clip so UI can play them
    for idx, clip in enumerate(final_clips):
        start = clip['start']
        end = clip['end']
        duration = end - start
        temp_clip = os.path.join(temp_dir, f"temp_clip_{idx}.mp4")
        subprocess.run([
            "ffmpeg", "-ss", str(start), "-i", video_path, "-t", str(duration),
            "-c:v", "libx264", "-preset", "ultrafast", "-crf", "35",
            "-c:a", "libmp3lame", "-b:a", "64k",
            "-y", temp_clip
        ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
    if progress_callback: progress_callback(100, "Â¡Proceso semÃ¡ntico terminado!")
    return final_clips, total_input_tokens, total_output_tokens

