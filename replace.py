import re, json

with open('pipeline.py', 'r', encoding='utf-8') as f:
    text = f.read()

target_regex = r"    full_text = \"\".*?for c in clips_list:"

replacement = '''    CHUNK_DUR = 1800 # 30 minutes per chunk
    chunks = []
    current_chunk_text = ""
    current_chunk_start = 0.0
    
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
                chunks.append(current_chunk_text)
                current_chunk_text = ""
                current_chunk_start = start
            current_chunk_text += f"[{seg['start']:.1f} - {seg['end']:.1f}] {seg['text']}\\n"
            
    if current_chunk_text.strip():
        chunks.append(current_chunk_text)
        
    if not chunks:
        print("Todo el texto esta excluido por clips anteriores. No hay nada nuevo que analizar.")
        return [], 0, 0
        
    link_instruction = "que SIEMPRE termine con 'Podes ver el video completo haciendo click en el link' seguida de los " if "gourmet" in video_path.lower() else ""
    
    total_input_tokens = 0
    total_output_tokens = 0
    final_clips = []
    
    clips_per_chunk = max(3, int(max_clips / len(chunks)) + 1)
    
    for chunk_idx, chunk_text in enumerate(chunks):
        if progress_callback: progress_callback(70 + int(20 * (chunk_idx / len(chunks))), f"Analizando bloque {chunk_idx+1}/{len(chunks)} con Gemini 2.5 Flash...")
        
        sys_prompt = f"Eres Leito4Gaming, un streamer y creador de videos virales de gaming de Argentina. Estas creando metadatos para tus propios clips, de juegos que TU MISMO jugaste (NOMBRE DEL JUEGO: {video_basename}). CRITICO: Escribe SIEMPRE en Español Argentino autentico (rioplatense). NO uses español neutro. NUNCA uses la palabra o conjugaciones de 'tu' (ej: nunca digas 'Te ha pasado', debes decir 'Te paso', 'Mira', 'Fijate'). Habla siempre tratando de VOS. Usa modismos locales ('cagazo', 'la puta madre'). EVITA 'che' y NUNCA uses 'boludo'. NUNCA asumas que no jugaste el juego ('Me contaron'). Escribe como un gamer con actitud, en PRIMERA PERSONA. Recibes una seccion de la transcripcion. Encuentra hasta {clips_per_chunk} clips DIVERTIDOS o BUENOS basandote en el prompt. IMPORTANTE: Clips entre 35 y 75 segundos. Asegurate de abarcar TODO el contexto (el inicio de la anecdota o explicacion) para que tenga sentido. No cortes las oraciones a la mitad. Devuelve UNICAMENTE lista JSON valida. Formato: [{{\\"start\\": float, \\"end\\": float, \\"reason\\": \\"string corto\\", \\"virality_score\\": int (70-99), \\"transcript\\": \\"string\\", \\"social_title\\": \\"Titulo ingenioso y directo que resuma EXACTAMENTE lo que pasa o se dice en el clip\\", \\"social_desc\\": \\"Descripcion MUY CORTA de APENAS UN RENGLON (max 10 palabras) que tenga sentido con el clip, en PRIMERA PERSONA. {link_instruction} Luego pon solo 3 hashtags populares del juego\\", \\"yt_title\\": \\"Titulo super llamativo para YouTube Shorts\\", \\"yt_desc\\": \\"Descripcion CORTA en PRIMERA PERSONA\\", \\"yt_tags\\": \\"Etiquetas SIN hashtag, incluye Leito4Gaming, Leito4GamingPlus y tags del juego real\\"}}]. Respeta estrictamente JSON, sin markdown. FUNDAMENTAL: Los titulos y descripciones DEBEN referirse ESTRICTAMENTE al dialogo del clip. Cita tus propias palabras en la descripcion."
        sys_prompt += get_feedback_injection()
        
        prompt_text = f"PROMPT DEL USUARIO: {prompt}\\n\\nAqui tienes la transcripcion del bloque {chunk_idx+1}:\\n\\n{chunk_text}"
        
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
            match = re.search(r'\\[.*\\]', txt, re.DOTALL)
            if match:
                clips_list = json.loads(match.group(0))
                for c in clips_list:'''

new_text = re.sub(target_regex, replacement, text, flags=re.DOTALL)
with open('pipeline.py', 'w', encoding='utf-8') as f:
    f.write(new_text)

print("Replaced!")
