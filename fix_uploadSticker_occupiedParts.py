with open('templates/index.html', 'r', encoding='utf-8') as f:
    text = f.read()

target = '''                    let occupiedParts = [];
                    editorStickers.forEach(st => {
                        if (st.type !== 'text') {
                            let relStart = st.start - currentClip.start;
                            let partIdx = Math.floor(relStart / partDur);
                            occupiedParts.push(partIdx);
                        }
                    });'''

replacement = '''                    let occupiedParts = [];
                    editorStickers.forEach(st => {
                        if (st.type !== 'text') {
                            let relStart = st.start;
                            let partIdx = Math.floor(relStart / partDur);
                            occupiedParts.push(partIdx);
                        }
                    });'''

text = text.replace(target, replacement)

with open('templates/index.html', 'w', encoding='utf-8') as f:
    f.write(text)
print("uploadSticker occupiedParts fixed")
