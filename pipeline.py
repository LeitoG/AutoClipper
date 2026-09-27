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
    temp_wav = os.path.join(temp_dir, "full_audio_temp.wav")
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
    
    if len(valid_segments) > 0:
        valid_segments.sort(key=lambda seg: np.max(rms_array[seg[0]:seg[1]]), reverse=True)
        valid_segments = valid_segments[:max_clips] # Limitar a los más fuertes para evitar horas de procesamiento
        valid_segments.sort(key=lambda x: x[0])
        
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
            
    valid_segments = valid_segments_filtered
    print(f"Tras aplicar zonas de exclusión (clips previos/actuales), quedan {len(valid_segments)} segmentos a evaluar.")
    
    if len(valid_segments) == 0:
        return [], 0, 0
        
    total_input_tokens = 0
    total_output_tokens = 0
    
    link_instruction = "que SIEMPRE termine con 'Podes ver el video completo haciendo click en el link' seguida de los " if "gourmet" in video_path.lower() else ""
    sys_prompt = f"Eres Leito4Gaming, un streamer y creador de videos virales de gaming de Argentina. Estás creando metadatos para tus propios clips, de juegos que TÚ MISMO jugaste (NOMBRE DEL JUEGO: {video_basename}). CRÍTICO: Escribe SIEMPRE en Español Argentino auténtico (rioplatense). NO uses español neutro. NUNCA uses la palabra o conjugaciones de 'tú' (ej: nunca digas 'Te ha pasado', debes decir 'Te pasó', 'Mirá', 'Fijate'). Habla siempre tratando de VOS. Usa modismos locales ('cagazo', 'la puta madre'). EVITA 'che' y NUNCA uses 'boludo'. NUNCA asumas que no jugaste el juego ('Me contaron'). Escribe como un gamer con actitud, en PRIMERA PERSONA. Recibes el audio y fotogramas. Evalúa si es BUENO o DIVERTIDO según el prompt. Si es silencio, responde 'RECHAZADO'. Si tiene valor, devuelve JSON: 'start' (float, inicio, sumale offset), 'end' (float, fin, sumale offset), 'reason' (string), 'virality_score' (int 70-99), 'transcript' (string), 'social_title' (string, Título muy gracioso para TikTok/IG en español argentino), 'social_desc' (string, descripción CORTA y directa en PRIMERA PERSONA, {link_instruction} usa SOLO hashtags genéricos, súper populares del juego y de gaming, PROHIBIDO INVENTAR hashtags sobre nombres de amigos o chistes internos (ej: PROHIBIDO #KEVINELMUTANTE), usa solo tags de millones de vistas), 'yt_title' (string, llamativo para YT Shorts), 'yt_desc' (string, descripción CORTA), 'yt_tags' (string, separadas por coma, incluye 'Leito4Gaming' y 'Leito4GamingPlus' y tags del juego real). IMPORTANTE: Clip entre 35 y 75 segundos. DEBES RETROCEDER LO SUFICIENTE para incluir TODO el contexto previo necesario (la preparación del chiste o susto). No cortes las oraciones a la mitad. FUNDAMENTAL: Los títulos y descripciones DEBEN referirse ESTRICTAMENTE a lo que se dice o pasa en el clip. Usa frases de tu propio diálogo en la descripción para que no suene genérico."
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
        while g_audio.state and "PROCESSING" in str(g_audio.state):
            time.sleep(2)
            g_audio = client.files.get(name=g_audio.name)
            
        if progress_callback: progress_callback(base_percent + 4, f"Evaluando clip {idx+1}/{len(valid_segments)} con Gemini 2.5 Flash...")
        print(f"Evaluando clip {idx} con Gemini 2.5 Flash...")
        
        prompt_text = f"OFFSET ORIGINAL: Este clip empieza en el segundo {start} del video original. Tienes que devolver tu 'start' entre {start} y {end}.\n\nPROMPT DEL USUARIO: {prompt}"
        
        response = None
        for attempt in range(4):
            try:
                response = client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=[g_audio] + frames_extracted + [sys_prompt, prompt_text],
                    config={
                        "temperature": 0.3,
                        "safety_settings": [
                            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
                            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
                            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
                            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"}
                        ]
                    }
                )
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


def analyze_video_semantic(video_path, prompt, api_key, temp_dir, progress_callback=None, exclusion_zones=None, incremental_save_cb=None, max_clips=15):
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
    
    if os.path.exists(transcript_file):
        if progress_callback: progress_callback(10, "Cargando transcripciÃ³n previa de la cachÃ©...")
        print("Cargando transcripciÃ³n cacheada...")
        with open(transcript_file, "r", encoding="utf-8") as f:
            transcript_segments = json.load(f)
    else:
        if progress_callback: progress_callback(10, "Extrayendo audio para Whisper...")
        temp_wav = os.path.join(temp_dir, f"{video_basename}_full.wav")
        if not os.path.exists(temp_wav):
            subprocess.run([
                "ffmpeg", "-i", video_path,
                "-vn", "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le",
                "-y", temp_wav
            ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
        if progress_callback: progress_callback(30, "Transcribiendo audio con Whisper (Esto puede tardar)...")
        print("Cargando modelo Whisper...")
        model = whisper.load_model("small")
        print("Transcribiendo...")
        result = model.transcribe(temp_wav, word_timestamps=False, verbose=True)
        transcript_segments = result["segments"]
        
        with open(transcript_file, "w", encoding="utf-8") as f:
            json.dump(transcript_segments, f, indent=4, ensure_ascii=False)
            
    # Formatear transcripciÃ³n para Gemini
    if progress_callback: progress_callback(70, "Analizando contexto con Gemini 2.5 Flash...")
    
    full_text = ""
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
            full_text += f"[{seg['start']:.1f} - {seg['end']:.1f}] {seg['text']}\n"
            
    if not full_text.strip():
        print("Todo el texto está excluido por clips anteriores. No hay nada nuevo que analizar.")
        return [], 0, 0
        
    link_instruction = "que SIEMPRE termine con 'Podes ver el video completo haciendo click en el link' seguida de los " if "gourmet" in video_path.lower() else ""
    sys_prompt = f"Eres Leito4Gaming, un streamer y creador de videos virales de gaming de Argentina. Estás creando metadatos para tus propios clips, de juegos que TÚ MISMO jugaste (NOMBRE DEL JUEGO: {video_basename}). CRÍTICO: Escribe SIEMPRE en Español Argentino auténtico (rioplatense). NO uses español neutro. NUNCA uses la palabra o conjugaciones de 'tú' (ej: nunca digas 'Te ha pasado', debes decir 'Te pasó', 'Mirá', 'Fijate'). Habla siempre tratando de VOS. Usa modismos locales ('cagazo', 'la puta madre'). EVITA 'che' y NUNCA uses 'boludo'. NUNCA asumas que no jugaste el juego ('Me contaron'). Escribe como un gamer con actitud, en PRIMERA PERSONA. Recibes la transcripción completa. Encuentra hasta {max_clips} clips DIVERTIDOS o BUENOS basándote en el prompt. IMPORTANTE: Clips entre 35 y 75 segundos. Asegúrate de abarcar TODO el contexto (el inicio de la anécdota o explicación) para que tenga sentido. No cortes las oraciones a la mitad. Devuelve ÚNICAMENTE lista JSON válida. Formato: [{{\"start\": float, \"end\": float, \"reason\": \"string corto\", \"virality_score\": int (70-99), \"transcript\": \"string\", \"social_title\": \"Título muy gracioso y viral para TikTok/IG en español argentino auténtico\", \"social_desc\": \"Descripción CORTA y directa para TikTok/IG en PRIMERA PERSONA, {link_instruction} usa SOLO hashtags genéricos, súper populares del juego y de gaming, PROHIBIDO INVENTAR hashtags sobre nombres de amigos o chistes internos (ej: PROHIBIDO #KEVINELMUTANTE), usa solo tags de millones de vistas\", \"yt_title\": \"Título súper llamativo para YouTube Shorts\", \"yt_desc\": \"Descripción CORTA en PRIMERA PERSONA\", \"yt_tags\": \"Etiquetas SIN hashtag, incluye Leito4Gaming, Leito4GamingPlus y tags del juego real\"}}]. Respeta estrictamente JSON, sin markdown. FUNDAMENTAL: Los títulos y descripciones DEBEN referirse ESTRICTAMENTE al diálogo del clip. Cita tus propias palabras en la descripción."
    sys_prompt += get_feedback_injection()
    
    prompt_text = f"PROMPT DEL USUARIO: {prompt}\n\nAquÃ­ tienes la transcripciÃ³n completa:\n\n{full_text}"
    
    total_input_tokens = 0
    total_output_tokens = 0
    final_clips = []
    
    try:
        response = None
        for attempt in range(4):
            try:
                response = client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=[sys_prompt, prompt_text],
                    config={
                        "temperature": 0.3,
                        "safety_settings": [
                            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
                            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
                            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
                            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"}
                        ]
                    }
                )
                break
            except Exception as e:
                err_str = str(e)
                if "limit: 0" in err_str:
                    raise Exception("QUOTA_AGOTADA: Has superado el límite gratuito diario o Google aún no procesa tu prepago. Debes esperar.")
                if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str:
                    if progress_callback: progress_callback(75, f"Límite API alcanzado. Pausando 45s...")
                    print(f"Límite de API alcanzado (429). Esperando 45 segundos... (Intento {attempt+1})")
                    time.sleep(45)
                else:
                    raise e
                    
        if response is None:
            raise Exception("Límite de API excedido continuamente.")
            
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

