with open('templates/index.html', 'r', encoding='utf-8') as f:
    text = f.read()

target = '''        function updateClipTimes(clip) {'''

replacement = '''        async function discardClip(clipId, event) {
            event.stopPropagation();
            const clip = clipsData.find(c => c.id === clipId);
            if (!clip) return;
            
            try {
                await fetch('/delete_clip', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ clip_id: clipId, video_name: document.getElementById('video-selector').value })
                });
                
                clipsData = clipsData.filter(x => x.id !== clipId);
                renderSidebar();
            } catch(err) {
                console.error(err);
            }
        }
        
        function updateClipTimes(clip) {'''

text = text.replace(target, replacement)

with open('templates/index.html', 'w', encoding='utf-8') as f:
    f.write(text)
print("Added discardClip function")
