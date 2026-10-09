with open('pipeline.py', 'r', encoding='utf-8') as f:
    text = f.read()
idx = text.find('for c in clips_list:')
if idx != -1:
    print(text[idx-200:idx+800])
