with open('templates/index.html', 'r', encoding='utf-8') as f:
    text = f.read()

idx = text.find('Array.from(folders.keys()).sort().forEach(f => {')
print(text[idx-100:idx+300])
