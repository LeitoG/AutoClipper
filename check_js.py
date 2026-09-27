import re
import subprocess
import os

with open(r'c:\Users\leone\Desktop\OBS Grabaciones\Exports\Complete Games\templates\index.html', 'r', encoding='utf-8') as f:
    text = f.read()

scripts = re.findall(r'<script>(.*?)</script>', text, re.DOTALL)
for i, s in enumerate(scripts):
    with open(f'script_{i}.js', 'w', encoding='utf-8') as f:
        f.write(s)
    
    print(f"Checking script {i}...")
    try:
        subprocess.run(['node', '-c', f'script_{i}.js'], check=True)
    except subprocess.CalledProcessError:
        print("SYNTAX ERROR IN SCRIPT", i)
    except FileNotFoundError:
        print("Node not installed.")
        break
