with open('templates/index.html', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for i, line in enumerate(lines):
    if ";    <div id=\"controls-\"" in line:
        lines[i] = line.replace(";    <div", "                        <div")

with open('templates/index.html', 'w', encoding='utf-8') as f:
    f.writelines(lines)
print("Line 1206 fixed")
