with open('pipeline.py', 'r', encoding='utf-8') as f:
    text = f.read()

text = text.replace('current_chunk_text += f"[{seg[\'start\']:.1f} - {seg[\'end\']:.1f}] {seg[\'text\']}\n"', 'current_chunk_text += f"[{seg[\'start\']:.1f} - {seg[\'end\']:.1f}] {seg[\'text\']}\\n"')
text = text.replace('prompt_text = f"PROMPT DEL USUARIO: {prompt}\n\nAqui tienes la transcripcion del bloque {chunk_idx+1}:\n\n{chunk_text}"', 'prompt_text = f"PROMPT DEL USUARIO: {prompt}\\n\\nAqui tienes la transcripcion del bloque {chunk_idx+1}:\\n\\n{chunk_text}"')
text = text.replace('Formato: [{"start": float', 'Formato: [{{\\"start\\": float')
# Wait, let's just make sure strings are closed
