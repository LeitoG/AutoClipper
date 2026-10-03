with open('templates/index.html', 'r', encoding='utf-8') as f:
    text = f.read()

target = '''                start: currentClip.start,
                end: currentClip.end,'''
replacement = '''                start: 0,
                end: getTimelineDuration(),
                isRelative: true,'''
text = text.replace(target, replacement)

with open('templates/index.html', 'w', encoding='utf-8') as f:
    f.write(text)
print("Done step 3")
