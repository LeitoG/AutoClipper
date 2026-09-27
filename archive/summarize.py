import json

with open('full_transcription.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

text = ""
for d in data:
    text += f"[{d['start']:.0f}s - {d['end']:.0f}s] {d['text']}\n"

with open('transcript_summary.txt', 'w', encoding='utf-8') as f:
    f.write(text)
