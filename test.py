with open('templates/index.html', 'r', encoding='utf-8') as f:
    text = f.read()
idx = text.find('onclick="enterTrimMode')
if idx != -1:
    print(text[idx-200:idx+400])
