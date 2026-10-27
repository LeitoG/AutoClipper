import re

with open('backend.py', 'r', encoding='utf-8') as f:
    text = f.read()

target = '''        txt = response.text.replace('json', '').replace('', '').strip()
        data = json.loads(txt)'''
        
replacement = '''        txt = response.text
        # Extraer solo el JSON usando regex
        import re
        match = re.search(r'\{.*\}', txt, re.DOTALL)
        if match:
            txt = match.group(0)
        else:
            txt = txt.replace('`json', '').replace('`', '').strip()
            
        data = json.loads(txt)'''

text = text.replace(target, replacement)
with open('backend.py', 'w', encoding='utf-8') as f:
    f.write(text)
