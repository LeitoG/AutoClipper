import re

with open('pipeline.py', 'r', encoding='utf-8') as f:
    text = f.read()

target = r"\(El audio que escuchas abarca exactamente este mismo tramo\)"
replacement = r"(El video que ves abarca exactamente este mismo tramo)"
new_text = re.sub(target, replacement, text)

with open('pipeline.py', 'w', encoding='utf-8') as f:
    f.write(new_text)
print("Done")
