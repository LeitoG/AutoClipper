with open('templates/index.html', 'r', encoding='utf-8') as f:
    text = f.read()

target = '''                let currentStickerStart = currentClip.start;
                for(let s of parsed) {
                    let vidEl = null, imgEl = null;
                    
                    let stStart = currentStickerStart;
                    let defaultDur = s.duration || 5.0; 
                    if (s.duration === undefined && s.end !== undefined && s.start !== undefined) {
                        defaultDur = s.end - s.start;
                    }
                    let stEnd = Math.min(currentClip.end, stStart + defaultDur);
                    
                    // Siguiente sticker empieza despues de este
                    currentStickerStart = stEnd + 1.0;
                    if (currentStickerStart >= currentClip.end - 5) {
                        currentStickerStart = currentClip.start;
                    }'''

replacement = '''                let currentStickerStart = 0;
                for(let s of parsed) {
                    let vidEl = null, imgEl = null;
                    
                    let stStart = currentStickerStart;
                    let defaultDur = s.duration || 5.0; 
                    if (s.duration === undefined && s.end !== undefined && s.start !== undefined) {
                        defaultDur = s.end - s.start;
                    }
                    let totalDur = currentClip.end - currentClip.start;
                    let stEnd = Math.min(totalDur, stStart + defaultDur);
                    
                    // Siguiente sticker empieza despues de este
                    currentStickerStart = stEnd + 1.0;
                    if (currentStickerStart >= totalDur - 5) {
                        currentStickerStart = 0;
                    }'''

text = text.replace(target, replacement)

with open('templates/index.html', 'w', encoding='utf-8') as f:
    f.write(text)
print("Fixed loadStickersState relative time")
