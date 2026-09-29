import re

with open('pipeline.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

new_lines = []
for line in lines:
    if 'social_title' in line and 'social_desc' in line and 'yt_title' in line:
        if 'string, T' in line:
            line = re.sub(r"'social_title' \(string, T.*?, 'yt_title'", r"'social_title' (string, Titulo ingenioso y directo que resuma EXACTAMENTE lo que pasa o se dice en el clip), 'social_desc' (string, descripcion MUY CORTA de APENAS UN RENGLON (max 10 palabras) que tenga sentido con el clip, en PRIMERA PERSONA. {link_instruction} Luego pon solo 3 hashtags populares del juego), 'yt_title'", line)
        if '\\"social_title\\": \\"T' in line:
            line = re.sub(r'\\"social_title\\": \\"T.*?, \\"yt_title\\"', r'\"social_title\": \"Titulo ingenioso y directo que resuma EXACTAMENTE lo que pasa o se dice en el clip\", \"social_desc\": \"Descripcion MUY CORTA de APENAS UN RENGLON (max 10 palabras) que tenga sentido con el clip, en PRIMERA PERSONA. {link_instruction} Luego pon solo 3 hashtags populares del juego\", \"yt_title\"', line)
    new_lines.append(line)

with open('pipeline.py', 'w', encoding='utf-8') as f:
    f.writelines(new_lines)
print('Done')
