with open('pipeline.py', 'r', encoding='utf-8') as f:
    text = f.read()
idx = text.find('is_excluded = True')
if idx != -1:
    print(text[idx:idx+1500])
