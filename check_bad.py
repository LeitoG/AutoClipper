import re

with open(r'c:\Users\leone\Desktop\OBS Grabaciones\Exports\Complete Games\templates\index.html', 'r', encoding='utf-8', errors='ignore') as f:
    text = f.read()

nodes = re.findall(r'>([^<]+)<', text)
bad_nodes = [n.strip() for n in nodes if any(ord(c) > 127 for c in n) and n.strip()]
from collections import Counter
with open('bad_nodes.txt', 'w', encoding='utf-8') as f:
    for n, c in Counter(bad_nodes).most_common(100):
        f.write(repr(n) + '\n')
