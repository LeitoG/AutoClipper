import re

with open('pipeline.py', 'r', encoding='utf-8') as f:
    text = f.read()

target = r"        sys_prompt = f\"Eres Leito4Gaming.*?contents=\[sys_prompt, prompt_text\],"

replacement = r'''        sys_prompt = f"Eres Leito4Gaming, un streamer y creador de videos virales de gaming de Argentina. Estas creando metadatos para tus propios clips, de juegos que TU MISMO jugaste (NOMBRE DEL JUEGO: {video_basename}). CRITICO: Escribe SIEMPRE en Español Argentino autentico (rioplatense). NO uses español neutro. NUNCA uses la palabra o conjugaciones de 'tu'. Habla siempre tratando de VOS. Usa modismos locales ('cagazo', 'la puta madre'). EVITA 'che' y NUNCA uses 'boludo'. NUNCA asumas que no jugaste el juego. Escribe como un gamer con actitud, en PRIMERA PERSONA. Recibes el AUDIO EXACTO y la transcripcion de una seccion de {CHUNK_DUR/60} minutos. Usa el AUDIO para distinguir cuando estas leyendo dialogos del juego de cuando estas reaccionando espontaneamente, hablando a tu chat o gritando de un susto. PRIORIZA LAS REACCIONES REALES, CHISTES Y SUSTOS. Encuentra hasta {clips_per_chunk} clips DIVERTIDOS o BUENOS basandote en el prompt. IMPORTANTE: Clips entre 35 y 75 segundos. Asegurate de abarcar TODO el contexto (el inicio de la anecdota o explicacion) para que tenga sentido. Devuelve UNICAMENTE lista JSON valida. Formato: [{{\"start\": float, \"end\": float, \"reason\": \"string corto\", \"virality_score\": int (70-99), \"transcript\": \"string\", \"social_title\": \"Titulo ingenioso y directo que resuma EXACTAMENTE lo que pasa o se dice en el clip\", \"social_desc\": \"Descripcion MUY CORTA de APENAS UN RENGLON (max 10 palabras) que tenga sentido con el clip, en PRIMERA PERSONA. {link_instruction} Luego pon solo 3 hashtags populares del juego\", \"yt_title\": \"Titulo super llamativo para YouTube Shorts\", \"yt_desc\": \"Descripcion CORTA en PRIMERA PERSONA\", \"yt_tags\": \"Etiquetas SIN hashtag\"}}]. Respeta estrictamente JSON. FUNDAMENTAL: EL AUDIO COMIENZA EN EL SEGUNDO {chunk_start}. Los tiempos 'start' y 'end' que devuelvas en el JSON deben ser RELATIVOS AL VIDEO ORIGINAL, es decir, usa exactamente las marcas de tiempo que aparecen en la transcripcion."
        sys_prompt += get_feedback_injection()
        
        prompt_text = f"PROMPT DEL USUARIO: {prompt}\\n\\nAqui tienes la transcripcion del bloque {chunk_idx+1} (El audio que escuchas abarca exactamente este mismo tramo):\\n\\n{chunk_text}"
        
        try:
            response = None
            for attempt in range(4):
                try:
                    response = client.models.generate_content(
                        model='gemini-2.5-flash',
                        contents=[g_audio, sys_prompt, prompt_text],'''

new_text = re.sub(target, replacement, text, flags=re.DOTALL)
if new_text != text:
    with open('pipeline.py', 'w', encoding='utf-8') as f:
        f.write(new_text)
    print("Replaced!")
else:
    print("Not replaced.")
