with open('templates/index.html', 'r', encoding='utf-8') as f:
    text = f.read()

target = '''el.style = position: absolute; left: %; width: %; height: 100%; background: #2080df; border: 1px solid #000; border-radius: 2px; color: #fff; font-size: 9px; display: flex; align-items: center; justify-content: space-between; overflow: hidden;;'''

replacement = '''el.style = position: absolute; left: %; width: %; height: 100%; background: #2080df; border: 1px solid #000; border-radius: 2px; color: #fff; font-size: 9px; display: flex; align-items: center; justify-content: space-between; overflow: hidden; box-sizing: border-box;;'''

text = text.replace(target, replacement)

with open('templates/index.html', 'w', encoding='utf-8') as f:
    f.write(text)
print("Sticker border-box fixed")
