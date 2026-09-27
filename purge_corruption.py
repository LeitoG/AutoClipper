import re

with open(r'c:\Users\leone\Desktop\OBS Grabaciones\Exports\Complete Games\templates\index.html', 'r', encoding='utf-8', errors='ignore') as f:
    text = f.read()

valid_chars = set('áéíóúÁÉÍÓÚñÑüÜ¡¿✅🚀✨✂️🔗↩️↪️🗑️📑⏱️💸🔊🔇📸📝🪝🤡📱🎬🎚️🔙⚙️🕒💾')

def clean_char(c):
    if ord(c) < 128:
        return c
    if c in valid_chars:
        return c
    return ''

cleaned_text = ''.join(clean_char(c) for c in text)

with open(r'c:\Users\leone\Desktop\OBS Grabaciones\Exports\Complete Games\templates\index.html', 'w', encoding='utf-8') as f:
    f.write(cleaned_text)

print("Purged corruption")
