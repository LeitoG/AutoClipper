with open('templates/index.html', 'r', encoding='utf-8') as f:
    text = f.read()

text = text.replace('transcriptText = editorWords.map(w => w.word).join(" ");', 'transcriptText = editorWords.map(w => w.text || w.word).join(" ");')

with open('templates/index.html', 'w', encoding='utf-8') as f:
    f.write(text)
print("Fixed transcript property")
