with open('templates/index.html', 'r', encoding='utf-8') as f:
    text = f.read()

text = text.replace(";    <div id=\"controls-\"", "                        <div id=\"controls-\"")

with open('templates/index.html', 'w', encoding='utf-8') as f:
    f.write(text)
print("Line 1206 fixed")
