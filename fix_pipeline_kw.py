import re

with open('pipeline.py', 'r', encoding='utf-8') as f:
    text = f.read()

target1 = r"def analyze_video_semantic\(video_path, prompt, api_key, temp_dir, progress_callback=None, exclusion_zones=None, incremental_save_cb=None, max_clips=15\):"
rep1 = r"def analyze_video_semantic(video_path, prompt, api_key, temp_dir, progress_callback=None, exclusion_zones=None, incremental_save_cb=None, max_clips=15, keywords=''):"
text = re.sub(target1, rep1, text)

target2 = r"sys_prompt = f\"Eres Leito4Gaming.*?{clips_instruction} basandote en el prompt\.\""

rep2 = r'''
        kw_instruction = ""
        if keywords.strip():
            kw_instruction = f" ATENCION ESPECIAL: El usuario ha proveido el siguiente GLOSARIO / PALABRAS CLAVE del juego: '{keywords}'. Debes buscar activamente fragmentos donde se mencionen estas palabras y priorizarlas X10 veces por sobre otros clips."
            
        sys_prompt = f"Eres Leito4Gaming, un streamer y creador de videos virales de gaming de Argentina. Estas creando metadatos para tus propios clips, de juegos que TU MISMO jugaste (NOMBRE DEL JUEGO: {video_basename}). CRITICO: Escribe SIEMPRE en Español Argentino autentico (rioplatense). NO uses español neutro. NUNCA uses la palabra o conjugaciones de 'tu'. Habla siempre tratando de VOS. Usa modismos locales ('cagazo', 'la puta madre'). EVITA 'che' y NUNCA uses 'boludo'. NUNCA asumas que no jugaste el juego. Escribe como un gamer con actitud, en PRIMERA PERSONA. Recibes el AUDIO EXACTO y la transcripcion de una seccion de {CHUNK_DUR/60} minutos. Usa el AUDIO para distinguir cuando estas leyendo dialogos del juego de cuando estas reaccionando espontaneamente, hablando a tu chat o gritando de un susto. PRIORIZA LAS REACCIONES REALES, CHISTES Y SUSTOS.{kw_instruction} {clips_instruction} basandote en el prompt."
'''
text = re.sub(target2, rep2, text, flags=re.DOTALL)

with open('pipeline.py', 'w', encoding='utf-8') as f:
    f.write(text)
print("Updated pipeline.py")
