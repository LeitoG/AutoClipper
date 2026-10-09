with open('templates/index.html', 'r', encoding='utf-8') as f:
    text = f.read()

target = '''            const stickersTrack = document.getElementById('stickers-track');
            if(stickersTrack) {
                stickersTrack.innerHTML = '';'''

replacement = '''            const soundsTrack = document.getElementById('sounds-track');
            if(soundsTrack) {
                soundsTrack.innerHTML = '<div style="position: absolute; left: 5px; top: 5px; font-size: 10px; color: #555; pointer-events: none;">Pista de Sonidos</div>';
                
                soundsTrack.onclick = (e) => {
                    if (e.target !== soundsTrack) return;
                    const rect = soundsTrack.getBoundingClientRect();
                    const perc = (e.clientX - rect.left) / rect.width;
                    workspaceVideo.currentTime = relToAbs(totalDur * perc);
                };
                
                editorSounds.forEach((snd) => {
                    if (snd.start === undefined) snd.start = 0;
                    if (snd.end === undefined) snd.end = totalDur;
                    
                    const sPerc = (snd.start / totalDur) * 100;
                    const wPerc = ((snd.end - snd.start) / totalDur) * 100;
                    
                    const el = document.createElement('div');
                    el.style = \position: absolute; left: \%; width: \%; height: 100%; background: #00aa55; border: 1px solid #000; border-radius: 2px; color: #fff; font-size: 9px; display: flex; align-items: center; justify-content: space-between; overflow: hidden; box-sizing: border-box;\;
                    
                    const leftH = document.createElement('div');
                    leftH.style = 'width: 5px; height: 100%; cursor: w-resize; background: rgba(0,0,0,0.2);';
                    leftH.onmousedown = (e) => startSoundDrag(e, snd, 'left');
                    const cLabel = document.createElement('div');
                    cLabel.innerText = snd.name || 'Audio';
                    cLabel.style = 'flex: 1; text-align: center; cursor: move; user-select: none;';
                    cLabel.onmousedown = (e) => startSoundDrag(e, snd, 'move');
                    const rightH = document.createElement('div');
                    rightH.style = 'width: 5px; height: 100%; cursor: e-resize; background: rgba(0,0,0,0.2);';
                    rightH.onmousedown = (e) => startSoundDrag(e, snd, 'right');
                    
                    el.appendChild(leftH);
                    el.appendChild(cLabel);
                    el.appendChild(rightH);
                    soundsTrack.appendChild(el);
                });
            }
            
            const stickersTrack = document.getElementById('stickers-track');
            if(stickersTrack) {
                stickersTrack.innerHTML = '';'''

text = text.replace(target, replacement)

with open('templates/index.html', 'w', encoding='utf-8') as f:
    f.write(text)
print("soundsTrack render added")
