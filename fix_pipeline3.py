import re

with open('pipeline.py', 'r', encoding='utf-8') as f:
    text = f.read()

target = '''    if len(valid_segments) > 0:
        valid_segments.sort(key=lambda seg: np.max(rms_array[seg[0]:seg[1]]), reverse=True)
        valid_segments = valid_segments[:max_clips] # Limitar a los mas fuertes para evitar horas de procesamiento
        valid_segments.sort(key=lambda x: x[0])'''

replacement = '''    if len(valid_segments) > 0:
        valid_segments.sort(key=lambda seg: np.max(rms_array[seg[0]:seg[1]]), reverse=True)
        limit = max_clips if max_clips > 0 else 30
        valid_segments = valid_segments[:limit] # Limitar a los mas fuertes para evitar horas de procesamiento
        valid_segments.sort(key=lambda x: x[0])'''

import re
# Regex to ignore accents
target_regex = r"    if len\(valid_segments\) > 0:\s*valid_segments\.sort\(key=lambda seg: np\.max\(rms_array\[seg\[0\]:seg\[1\]\]\), reverse=True\)\s*valid_segments = valid_segments\[:max_clips\].*?\s*valid_segments\.sort\(key=lambda x: x\[0\]\)"

new_text = re.sub(target_regex, replacement, text, flags=re.DOTALL)
if new_text != text:
    with open('pipeline.py', 'w', encoding='utf-8') as f:
        f.write(new_text)
    print("Replaced!")
else:
    print("Not replaced.")
