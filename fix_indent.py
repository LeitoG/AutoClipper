import re

with open('pipeline.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

in_chunk = False
for i, line in enumerate(lines):
    if 'for chunk_idx, chunk_text in enumerate(chunks):' in line:
        in_chunk = True
    elif in_chunk:
        if line.startswith('        else:'):
            lines[i] = '    ' + line
        elif line.startswith('            if "RECHAZADO" in txt or len(txt) > 0:'):
            lines[i] = '    ' + line
        elif line.startswith('                print(f"Gemini no devolvi'):
            lines[i] = '    ' + line
        elif line.startswith('                raise Exception(f"Gemini respondi'):
            lines[i] = '    ' + line
        elif line.startswith('    except Exception as e:'):
            lines[i] = '    ' + line
        elif line.startswith('        print(f"Error de Gemini: {e}")'):
            lines[i] = '    ' + line
        elif line.startswith('        raise Exception(f"Error procesando la transcripc'):
            lines[i] = '    ' + line
            in_chunk = False

with open('pipeline.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)
print("Indentation fixed.")
