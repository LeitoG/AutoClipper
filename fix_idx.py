with open("templates/index.html", "r", encoding="utf-8") as f:
    text = f.read()

target = '<span>Clip ${idx + 1} <span style="font-size:12px; color:#aaa;">(${clip.id})</span></span>'
replacement = '<span>Clip ${clip.id.replace("clip_", "")} <span style="font-size:12px; color:#aaa;">(${clip.id})</span></span>'
text = text.replace(target, replacement)

with open("templates/index.html", "w", encoding="utf-8") as f:
    f.write(text)
print("Fixed idx replacement")
