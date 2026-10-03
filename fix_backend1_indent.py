with open('backend.py', 'r', encoding='utf-8') as f:
    text = f.read()

lines = text.split('\n')
for i in range(1115, 1177):
    # Unindent by 8 spaces
    if lines[i].startswith('        '):
        lines[i] = lines[i][8:]

text = '\n'.join(lines)
with open('backend.py', 'w', encoding='utf-8') as f:
    f.write(text)
print("Part 1 unindent done")
