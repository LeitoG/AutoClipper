with open('templates/index.html', 'r', encoding='utf-8') as f:
    lines = f.readlines()

lines[1205] = '                        <div id="controls-" style="display:none; flex-direction:column; gap:8px; margin-top: 15px; background: #1a1a1a; padding: 12px; border-radius: 4px; border: 1px solid #444;">\n'

with open('templates/index.html', 'w', encoding='utf-8') as f:
    f.writelines(lines)
print("Line 1206 fixed manually")
