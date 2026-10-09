with open('backend.py', 'r', encoding='utf-8') as f:
    text = f.read()

target = '''                "-filter_complex", f"[0:a:{tv}]volume={req.vol_voz}[a1];[0:a:{tj}]volume={req.vol_juego}[a2];[a1][a2]amix=inputs=2:duration=first:dropout_transition=0[a]",'''

replacement = '''                "-filter_complex", f"[0:a:{tv}]volume={req.vol_voz}[a1];[0:a:{tj}]volume={req.vol_juego}[a2];[a1][a2]amix=inputs=2:duration=first:dropout_transition=0,volume=2[a]",'''

text = text.replace(target, replacement)

with open('backend.py', 'w', encoding='utf-8') as f:
    f.write(text)
print("Updated preview_audio_mix volume logic")
