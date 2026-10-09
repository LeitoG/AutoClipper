with open('pipeline.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()
for i in range(435, 455):
    print(f"{i+1}: {repr(lines[i])}")
