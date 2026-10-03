with open('templates/index.html', 'r', encoding='utf-8') as f:
    text = f.read()

target = '''                const relTime = absToRel(cTime);
                editorSounds.forEach(snd => {'''

replacement = '''                editorSounds.forEach(snd => {'''

if target in text:
    text = text.replace(target, replacement)
    with open('templates/index.html', 'w', encoding='utf-8') as f:
        f.write(text)
    print("Done")
else:
    print("Target not found")
