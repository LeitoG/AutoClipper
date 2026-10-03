with open('templates/index.html', 'r', encoding='utf-8') as f:
    text = f.read()

target = '''        function onStickerDrag(e) {
            if(!draggingSticker) return;
            const track = document.getElementById('stickers-track');
            const totalDur = currentClip.end - currentClip.start;
            const trackWidth = track.getBoundingClientRect().width;
            const dx = e.clientX - stickerDragStartX;
            const dt = (dx / trackWidth) * totalDur;
            
            if (draggingStickerHandle === 'left') {
                draggingSticker.start = Math.max(currentClip.start, Math.min(draggingSticker.end - 0.1, stickerDragStartVal + dt));
                draggingSticker.duration = draggingSticker.end - draggingSticker.start;
            } else if (draggingStickerHandle === 'right') {
                draggingSticker.end = Math.max(draggingSticker.start + 0.1, Math.min(currentClip.end, stickerDragStartVal + dt));
                draggingSticker.duration = draggingSticker.end - draggingSticker.start;
            } else if (draggingStickerHandle === 'move') {
                const w = stickerDragStartVal.e - stickerDragStartVal.s;
                let newS = stickerDragStartVal.s + dt;
                let newE = stickerDragStartVal.e + dt;
                if (newS < currentClip.start) {
                    newS = currentClip.start;
                    newE = newS + w;
                }
                if (newE > currentClip.end) {
                    newE = currentClip.end;
                    newS = newE - w;
                }'''

replacement = '''        function onStickerDrag(e) {
            if(!draggingSticker) return;
            const track = document.getElementById('stickers-track');
            const totalDur = getTimelineDuration();
            const trackWidth = track.getBoundingClientRect().width;
            const dx = e.clientX - stickerDragStartX;
            const dt = (dx / trackWidth) * totalDur;
            
            if (draggingStickerHandle === 'left') {
                draggingSticker.start = Math.max(0, Math.min(draggingSticker.end - 0.1, stickerDragStartVal + dt));
                draggingSticker.duration = draggingSticker.end - draggingSticker.start;
            } else if (draggingStickerHandle === 'right') {
                draggingSticker.end = Math.max(draggingSticker.start + 0.1, Math.min(totalDur, stickerDragStartVal + dt));
                draggingSticker.duration = draggingSticker.end - draggingSticker.start;
            } else if (draggingStickerHandle === 'move') {
                const w = stickerDragStartVal.e - stickerDragStartVal.s;
                let newS = stickerDragStartVal.s + dt;
                let newE = stickerDragStartVal.e + dt;
                if (newS < 0) {
                    newS = 0;
                    newE = newS + w;
                }
                if (newE > totalDur) {
                    newE = totalDur;
                    newS = newE - w;
                }'''

if target in text:
    text = text.replace(target, replacement)
    with open('templates/index.html', 'w', encoding='utf-8') as f:
        f.write(text)
    print("Done step 5")
else:
    print("Target not found")
