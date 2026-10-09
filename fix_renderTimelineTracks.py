with open('templates/index.html', 'r', encoding='utf-8') as f:
    text = f.read()

target = '''            loadStickersState();
            loadSoundsState();
            
            workspaceVideo.src ='''

replacement = '''            loadStickersState();
            loadSoundsState();
            renderTimelineTracks();
            
            workspaceVideo.src ='''

text = text.replace(target, replacement)

with open('templates/index.html', 'w', encoding='utf-8') as f:
    f.write(text)
print("renderTimelineTracks added after loading state")
