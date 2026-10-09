with open('templates/index.html', 'r', encoding='utf-8') as f:
    text = f.read()

target = '''                    let stStart = currentClip.start + (selectedPart * partDur);
                    let stEnd;
                    if (isVideo) {
                        stEnd = stStart + Math.min(mediaDuration, partDur);
                    } else {
                        stEnd = stStart + partDur;
                    }'''

replacement = '''                    let stStart = (selectedPart * partDur);
                    let stEnd;
                    if (isVideo) {
                        stEnd = stStart + Math.min(mediaDuration, partDur);
                    } else {
                        stEnd = stStart + partDur;
                    }'''

text = text.replace(target, replacement)

with open('templates/index.html', 'w', encoding='utf-8') as f:
    f.write(text)
print("uploadSticker fixed")
