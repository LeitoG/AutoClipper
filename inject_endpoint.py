import re

with open(r'c:\Users\leone\Desktop\OBS Grabaciones\Exports\Complete Games\backend.py', 'r', encoding='utf-8') as f:
    text = f.read()

with open('snippet.py', 'r', encoding='utf-8') as f:
    snippet = f.read()

if 'def get_clip_audio_track' not in text:
    text = text.replace('def preview_audio_mix(req: AudioPreviewRequest):', snippet + '\n\n' + 'def preview_audio_mix(req: AudioPreviewRequest):')

with open(r'c:\Users\leone\Desktop\OBS Grabaciones\Exports\Complete Games\backend.py', 'w', encoding='utf-8') as f:
    f.write(text)
