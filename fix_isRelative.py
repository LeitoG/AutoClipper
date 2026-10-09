with open('templates/index.html', 'r', encoding='utf-8') as f:
    text = f.read()

target1 = '''                start: stStart,
                end: stEnd,
                duration: 5.0,
                server_path: null,'''

replacement1 = '''                start: stStart,
                end: stEnd,
                duration: 5.0,
                isRelative: true,
                server_path: null,'''

text = text.replace(target1, replacement1)

target2 = '''                        start: stStart,
                        end: stEnd,
                        duration: defaultDur,
                        videoElement: vidEl,
                        imageElement: imgEl'''

replacement2 = '''                        start: stStart,
                        end: stEnd,
                        duration: defaultDur,
                        isRelative: true,
                        videoElement: vidEl,
                        imageElement: imgEl'''

text = text.replace(target2, replacement2)

with open('templates/index.html', 'w', encoding='utf-8') as f:
    f.write(text)
print("isRelative flag added to stickers")
