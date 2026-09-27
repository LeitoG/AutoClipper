import re

with open(r'c:\Users\leone\Desktop\OBS Grabaciones\Exports\Complete Games\templates\index.html', 'r', encoding='utf-8', errors='ignore') as f:
    text = f.read()

# Remove all non-ascii characters to fix the corruption once and for all!
# The user specifically said "No uses tildes en las palabras, eso creo que lo esta rompiendo tambien"

def to_ascii(c):
    if ord(c) < 128: return c
    return ''

cleaned = ''
for c in text:
    if ord(c) < 128:
        cleaned += c
    else:
        cleaned += '' # just drop it, no more tildes or emojis

# Now fix the text that got mushed together
cleaned = cleaned.replace('Ajuste de Cmara', 'Ajuste de Camara')
cleaned = cleaned.replace('> Cmara<', '> Camara<')
cleaned = cleaned.replace('>Cmara<', '>Camara<')
cleaned = cleaned.replace('Subttulos', 'Subtitulos')
cleaned = cleaned.replace('Configuracin', 'Configuracion')
cleaned = cleaned.replace('Duracin', 'Duracion')
cleaned = cleaned.replace('Generar Nuevos Clips<br>con IA', 'Generar Nuevos Clips<br>con IA')
cleaned = cleaned.replace('Cortar<br>Escena', 'Cortar<br>Escena')
cleaned = cleaned.replace('Eliminar<br>Escena', 'Eliminar<br>Escena')
cleaned = cleaned.replace('Duplicar<br>Escena', 'Duplicar<br>Escena')
cleaned = cleaned.replace('Gasto Estimado', 'Gasto Estimado')

with open(r'c:\Users\leone\Desktop\OBS Grabaciones\Exports\Complete Games\templates\index.html', 'w', encoding='utf-8') as f:
    f.write(cleaned)
