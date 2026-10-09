with open('templates/index.html', 'r', encoding='utf-8') as f:
    text = f.read()

target = '''                clipsData = clipsData.filter(x => x.id !== clipId);
                renderSidebar();'''

replacement = '''                rejectedClipsData.push(clip);
                clipsData = clipsData.filter(x => x.id !== clipId);
                renderSidebar();'''

text = text.replace(target, replacement)

target2 = '''                if (type === 'up') {
                    markClipDone(id, {checked: true});
                } else if (type === 'down') {
                    await fetch('/delete_clip', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({ clip_id: id, video_name: document.getElementById('video-selector').value })
                    });
                    clipsData = clipsData.filter(x => x.id !== id);
                    renderSidebar();
                }'''

replacement2 = '''                if (type === 'up') {
                    markClipDone(id, {checked: true});
                } else if (type === 'down') {
                    await fetch('/delete_clip', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({ clip_id: id, video_name: document.getElementById('video-selector').value })
                    });
                    const clipToReject = clipsData.find(c => c.id === id);
                    if (clipToReject) rejectedClipsData.push(clipToReject);
                    clipsData = clipsData.filter(x => x.id !== id);
                    renderSidebar();
                }'''

text = text.replace(target2, replacement2)

with open('templates/index.html', 'w', encoding='utf-8') as f:
    f.write(text)
print("Fixed rejectedClipsData local state")
