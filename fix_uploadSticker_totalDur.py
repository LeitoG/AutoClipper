with open('templates/index.html', 'r', encoding='utf-8') as f:
    text = f.read()

target = '''                    const totalDur = currentClip.end - currentClip.start;
                    const partDur = totalDur / 6;'''

replacement = '''                    const totalDur = getTimelineDuration();
                    const partDur = totalDur / 6;'''

text = text.replace(target, replacement)

with open('templates/index.html', 'w', encoding='utf-8') as f:
    f.write(text)
print("uploadSticker totalDur fixed")
