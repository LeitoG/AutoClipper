import re

with open('pipeline.py', 'r', encoding='utf-8') as f:
    text = f.read()

target_regex = r"    CHUNK_DUR = 1800.*?    for chunk_idx, chunk_text in enumerate\(chunks\):"

replacement = '''    CHUNK_DUR = 1800 # 30 minutes per chunk
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
    
    for chunk_idx, chunk_data in enumerate(chunks):
        chunk_start = chunk_data["start"]
        chunk_end = chunk_data["end"]
        chunk_text = chunk_data["text"]
'''

# Use python to do the replacement
new_text = re.sub(target_regex, replacement, text, flags=re.DOTALL)
if new_text != text:
    with open('pipeline.py', 'w', encoding='utf-8') as f:
        f.write(new_text)
    print("Replaced!")
else:
    print("Not replaced.")
