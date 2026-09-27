import re

with open(r'c:\Users\leone\Desktop\OBS Grabaciones\Exports\Complete Games\templates\index.html', 'r', encoding='utf-8') as f:
    text = f.read()

text = text.replace('Secuencia 3: Historial y Redes Sociales', 'Secuencia 4: Historial y Redes Sociales')

# Add a title to the sidebar for the Editor
title_html = '<div style="color: var(--accent-primary); font-size: 10px; text-align: center; font-weight: bold; padding: 0 5px; line-height: 1.2;">Secuencia 3:<br>Editor Completo</div>'
if 'Secuencia 3:<br>Editor Completo' not in text:
    text = text.replace('<button id="nav-btn-encuadre"', title_html + '\n            <button id="nav-btn-encuadre"')

with open(r'c:\Users\leone\Desktop\OBS Grabaciones\Exports\Complete Games\templates\index.html', 'w', encoding='utf-8') as f:
    f.write(text)
