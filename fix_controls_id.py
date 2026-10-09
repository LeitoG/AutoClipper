with open('templates/index.html', 'r', encoding='utf-8') as f:
    text = f.read()

target = '<div id="controls-" style="display:none;'
replacement = '<div id="controls-" style="display:none;'

text = text.replace(target, replacement)

with open('templates/index.html', 'w', encoding='utf-8') as f:
    f.write(text)
print("Fixed controls ID")
