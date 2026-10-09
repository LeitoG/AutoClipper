with open('templates/index.html', 'r', encoding='utf-8') as f:
    text = f.read()

target = '''        function onSoundDrag(e) {
            if(!draggingSound) return;
            const track = document.getElementById('sounds-track');
            const totalDur = currentClip.end - currentClip.start;
            const trackWidth = track.getBoundingClientRect().width;
            const dx = e.clientX - soundDragStartX;
            const dt = (dx / trackWidth) * totalDur;
            
            if (draggingSoundHandle === 'left') {
                draggingSound.start = Math.max(currentClip.start, Math.min(draggingSound.end - 0.1, soundDragStartVal + dt));
            } else if (draggingSoundHandle === 'right') {
                draggingSound.end = Math.max(draggingSound.start + 0.1, Math.min(currentClip.end, soundDragStartVal + dt));
            } else if (draggingSoundHandle === 'move') {
                const w = soundDragStartVal.e - soundDragStartVal.s;
                let newS = soundDragStartVal.s + dt;
                let newE = soundDragStartVal.e + dt;
                if (newS < currentClip.start) {
                    newS = currentClip.start;
                    newE = newS + w;
                }
                if (newE > currentClip.end) {
                    newE = currentClip.end;
                    newS = newE - w;
                }
                draggingSound.start = newS;
                draggingSound.end = newE;
            }
            renderTimelineTracks();
        }'''

replacement = '''        function onSoundDrag(e) {
            if(!draggingSound) return;
            const track = document.getElementById('sounds-track');
            const totalDur = getTimelineDuration();
            const trackWidth = track.getBoundingClientRect().width;
            const dx = e.clientX - soundDragStartX;
            const dt = (dx / trackWidth) * totalDur;
            
            if (draggingSoundHandle === 'left') {
                draggingSound.start = Math.max(0, Math.min(draggingSound.end - 0.1, soundDragStartVal + dt));
            } else if (draggingSoundHandle === 'right') {
                draggingSound.end = Math.max(draggingSound.start + 0.1, Math.min(totalDur, soundDragStartVal + dt));
            } else if (draggingSoundHandle === 'move') {
                const w = soundDragStartVal.e - soundDragStartVal.s;
                let newS = soundDragStartVal.s + dt;
                let newE = soundDragStartVal.e + dt;
                if (newS < 0) {
                    newS = 0;
                    newE = newS + w;
                }
                if (newE > totalDur) {
                    newE = totalDur;
                    newS = newE - w;
                }
                draggingSound.start = newS;
                draggingSound.end = newE;
            }
            renderTimelineTracks();
        }'''

text = text.replace(target, replacement)

with open('templates/index.html', 'w', encoding='utf-8') as f:
    f.write(text)
print("onSoundDrag fixed")
