with open('templates/index.html', 'r', encoding='utf-8') as f:
    text = f.read()

target = '''                savedData.forEach((s, idx) => {
                    let id = Date.now().toString() + "_" + idx;
                    let stStart = currentClip.start + (s.startOffset !== undefined ? s.startOffset : 0);
                    let stEnd = currentClip.start + (s.endOffset !== undefined ? s.endOffset : (s.end - (s.start || 0)));
                    if (stEnd > currentClip.end) stEnd = currentClip.end;
                    
                    editorStickers.push({
                        id: id,
                        name: s.name,
                        server_path: s.server_path,
                        url: s.url,
                        x: s.x,
                        y: s.y,
                        w: s.w,
                        h: s.h,
                        start: stStart,
                        end: stEnd,
                        type: s.type || 'image',
                        text: s.text,
                        color: s.color,
                        strokeColor: s.strokeColor,
                        font: s.font,
                        animIn: s.animIn,
                        animOut: s.animOut,
                        track: s.track || 0,
                        wordColors: s.wordColors, start: s.start, end: s.end, isRelative: s.isRelative, fontSize: s.fontSize,
                        duration: s.duration,
                        videoElement: null,
                        imageElement: null
                    });
                });
                
                // Cargar elementos HTML para los stickers (video/img)
                editorStickers.forEach(s => {
                    if (!s.isRelative) {
                        if (s.start !== undefined) s.start = absToRel(s.start);
                        else s.start = 0;
                        if (s.end !== undefined) s.end = absToRel(s.end);
                        else s.end = (s.duration || 5.0);
                        s.isRelative = true;
                    }'''

replacement = '''                let totalDur = currentClip.end - currentClip.start;
                savedData.forEach((s, idx) => {
                    let id = Date.now().toString() + "_" + idx;
                    
                    // Asegurar que usemos tiempos relativos (0 a totalDur)
                    let defaultDur = s.duration || 5.0;
                    if (s.duration === undefined && s.end !== undefined && s.start !== undefined) {
                        defaultDur = s.end - s.start;
                    }
                    let stStart = 0;
                    if (s.isRelative && s.start !== undefined) {
                        stStart = s.start;
                    }
                    let stEnd = stStart + defaultDur;
                    if (stEnd > totalDur) stEnd = totalDur;
                    
                    editorStickers.push({
                        id: id,
                        name: s.name,
                        server_path: s.server_path,
                        url: s.url,
                        x: s.x,
                        y: s.y,
                        w: s.w,
                        h: s.h,
                        type: s.type || 'image',
                        text: s.text,
                        color: s.color,
                        strokeColor: s.strokeColor,
                        font: s.font,
                        animIn: s.animIn,
                        animOut: s.animOut,
                        track: s.track || 0,
                        wordColors: s.wordColors,
                        fontSize: s.fontSize,
                        start: stStart,
                        end: stEnd,
                        isRelative: true,
                        duration: defaultDur,
                        videoElement: null,
                        imageElement: null
                    });
                });
                
                // Cargar elementos HTML para los stickers (video/img)
                editorStickers.forEach(s => {'''

text = text.replace(target, replacement)

with open('templates/index.html', 'w', encoding='utf-8') as f:
    f.write(text)
print("Fixed loadStickerPreset")
