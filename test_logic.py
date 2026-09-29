with open('templates/index.html', 'r', encoding='utf-8') as f:
    text = f.read()

idx = text.find('let lastFolder = localStorage.getItem(\'lastFolder\');')
print(text[idx-50:idx+800])
