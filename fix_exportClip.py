with open('templates/index.html', 'r', encoding='utf-8') as f:
    text = f.read()

target = '''                        vol_voz: document.getElementById('vol-voz') ? parseFloat(document.getElementById('vol-voz').value) : 1.0,
                        vol_juego: document.getElementById('vol-juego') ? parseFloat(document.getElementById('vol-juego').value) : 1.0,
                        social_title: document.getElementById('redes-titulo') ? document.getElementById('redes-titulo').value : null,'''

replacement = '''                        vol_voz: document.getElementById('vol-voz') ? parseFloat(document.getElementById('vol-voz').value) : 1.0,
                        vol_juego: document.getElementById('vol-juego') ? parseFloat(document.getElementById('vol-juego').value) : 1.0,
                        track_voz: 2,
                        track_juego: 3,
                        social_title: document.getElementById('redes-titulo') ? document.getElementById('redes-titulo').value : null,'''

text = text.replace(target, replacement)

with open('templates/index.html', 'w', encoding='utf-8') as f:
    f.write(text)
print("Updated exportClip to send track indices")
