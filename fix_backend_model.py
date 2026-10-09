with open('backend.py', 'r', encoding='utf-8') as f:
    text = f.read()

target = '''    export_track: Optional[str] = "mix"
    vol_voz: float = 1.0
    vol_juego: float = 1.0'''

replacement = '''    export_track: Optional[str] = "mix"
    vol_voz: float = 1.0
    vol_juego: float = 1.0
    track_voz: int = 2
    track_juego: int = 3'''

text = text.replace(target, replacement)

with open('backend.py', 'w', encoding='utf-8') as f:
    f.write(text)
print("Added track_voz and track_juego to ExportRequest")
