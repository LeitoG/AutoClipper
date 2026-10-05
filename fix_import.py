with open('backend.py', 'r', encoding='utf-8') as f:
    text = f.read()

text = text.replace('from fastapi import FastAPI, HTTPException', 'from fastapi import FastAPI, HTTPException, BackgroundTasks')

with open('backend.py', 'w', encoding='utf-8') as f:
    f.write(text)
print("Import added")
