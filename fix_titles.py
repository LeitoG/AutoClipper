import re

with open(r'c:\Users\leone\Desktop\OBS Grabaciones\Exports\Complete Games\templates\index.html', 'r', encoding='utf-8') as f:
    text = f.read()

text = text.replace('Auto Clipper V12</h2>', 'Secuencia 1: Menu Principal (Auto Clipper V12)</h2>')
text = text.replace('>Ajuste Preciso: ', '>Secuencia 2: Pre-Edicion (Ajuste Preciso): ')
text = text.replace('> Historial y Redes Sociales</h2>', '>Secuencia 3: Historial y Redes Sociales</h2>')

with open(r'c:\Users\leone\Desktop\OBS Grabaciones\Exports\Complete Games\templates\index.html', 'w', encoding='utf-8') as f:
    f.write(text)
