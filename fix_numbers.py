import re

with open(r'c:\Users\leone\Desktop\OBS Grabaciones\Exports\Complete Games\templates\index.html', 'r', encoding='utf-8') as f:
    text = f.read()

text = text.replace('<i></i>Encuadre', '<i></i>1. Encuadre')
text = text.replace('<i></i>Subtitulos', '<i></i>2. Subtitulos')
text = text.replace('<i></i>Gancho', '<i></i>3. Gancho')
text = text.replace('<i></i>Stickers', '<i></i>4. Stickers')
text = text.replace('<i></i>Redes', '<i></i>5. Redes')
text = text.replace('<i></i>Audio', '<i></i>6. Audio')
text = text.replace('<i></i>Final Img', '<i></i>7. Final Img')

with open(r'c:\Users\leone\Desktop\OBS Grabaciones\Exports\Complete Games\templates\index.html', 'w', encoding='utf-8') as f:
    f.write(text)
