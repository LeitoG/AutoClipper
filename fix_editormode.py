with open('templates/index.html', 'r', encoding='utf-8') as f:
    text = f.read()

target = '''            editorScenes = [{
                id: Date.now(),
                start: 0,
                end: getTimelineDuration(),
                isRelative: true,
                template: initialTemplate,
                cropState: defaultCrop
            }];'''

replacement = '''            editorScenes = [{
                id: Date.now(),
                start: 0,
                end: currentClip.end - currentClip.start,
                isRelative: true,
                template: initialTemplate,
                cropState: defaultCrop
            }];'''

text = text.replace(target, replacement)

with open('templates/index.html', 'w', encoding='utf-8') as f:
    f.write(text)
print("editorScenes initialization fixed")
