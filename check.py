import re

with open('pipeline.py', 'r', encoding='utf-8') as f:
    text = f.read()

target = '''    full_text = ""
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
            full_text += f"[{seg['start']:.1f} - {seg['end']:.1f}] {seg['text']}\\n"
            
    if not full_text.strip():
        print("Todo el texto está excluido por clips anteriores. No hay nada nuevo que analizar.")
        return [], 0, 0
        
    link_instruction = "que SIEMPRE termine con 'Podes ver el video completo haciendo click en el link' seguida de los " if "gourmet" in video_path.lower() else ""
    sys_prompt = f"Eres Leito4Gaming, un streamer y creador de videos virales de gaming de Argentina. Estás creando metadatos para tus propios clips, de juegos que TÚ MISMO jugaste (NOMBRE DEL JUEGO: {video_basename}). CRÍTICO: Escribe SIEMPRE en Español Argentino auténtico (rioplatense). NO uses español neutro. NUNCA uses la palabra o conjugaciones de 'tú' (ej: nunca digas 'Te ha pasado', debes decir 'Te pasó', 'Mirá', 'Fijate'). Habla siempre tratando de VOS. Usa modismos locales ('cagazo', 'la puta madre'). EVITA 'che' y NUNCA uses 'boludo'. NUNCA asumas que no jugaste el juego ('Me contaron'). Escribe como un gamer con actitud, en PRIMERA PERSONA. Recibes la transcripción completa. Encuentra hasta {max_clips} clips DIVERTIDOS o BUENOS basándote en el prompt. IMPORTANTE: Clips entre 35 y 75 segundos. Asegúrate de abarcar TODO el contexto (el inicio de la anécdota o explicación) para que tenga sentido. No cortes las oraciones a la mitad. Devuelve ÚNICAMENTE lista JSON válida. Formato: [{{\\"start\\": float, \\"end\\": float, \\"reason\\": \\"string corto\\", \\"virality_score\\": int (70-99), \\"transcript\\": \\"string\\", \\"social_title\\": \\"Titulo ingenioso y directo que resuma EXACTAMENTE lo que pasa o se dice en el clip\\", \\"social_desc\\": \\"Descripcion MUY CORTA de APENAS UN RENGLON (max 10 palabras) que tenga sentido con el clip, en PRIMERA PERSONA. {link_instruction} Luego pon solo 3 hashtags populares del juego\\", \\"yt_title\\": \\"Título súper llamativo para YouTube Shorts\\", \\"yt_desc\\": \\"Descripción CORTA en PRIMERA PERSONA\\", \\"yt_tags\\": \\"Etiquetas SIN hashtag, incluye Leito4Gaming, Leito4GamingPlus y tags del juego real\\"}}]. Respeta estrictamente JSON, sin markdown. FUNDAMENTAL: Los títulos y descripciones DEBEN referirse ESTRICTAMENTE al diálogo del clip. Cita tus propias palabras en la descripción."
    sys_prompt += get_feedback_injection()
    
    prompt_text = f"PROMPT DEL USUARIO: {prompt}\\n\\nAquí tienes la transcripción completa:\\n\\n{full_text}"
    
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
                    import time
                    time.sleep(45)
                else:
                    raise e
                    
        if response is None:
            raise Exception("Límite de API excedido continuamente.")
            
        if hasattr(response, 'usage_metadata') and response.usage_metadata:
            total_input_tokens += getattr(response.usage_metadata, 'prompt_token_count', 0)
            total_output_tokens += getattr(response.usage_metadata, 'candidates_token_count', 0)
        
        txt = response.text
        match = re.search(r'\\[.*\\]', txt, re.DOTALL)
        if match:
            clips_list = json.loads(match.group(0))
            for c in clips_list:'''

# Replace "Aquí" and others since they might have weird encodings
target_regex = r"    full_text = \"\".*?for c in clips_list:"

import re
matches = re.findall(target_regex, text, re.DOTALL)
if len(matches) != 1:
    print(f"Failed to match exactly one block. Found {len(matches)}")
else:
    print("Match found! Ready to replace.")
