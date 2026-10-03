import re

with open('templates/index.html', 'r', encoding='utf-8') as f:
    text = f.read()

# 1. Update saveStickersState to include start, end, isRelative
text = text.replace(
    '''wordColors: s.wordColors''',
    '''wordColors: s.wordColors, start: s.start, end: s.end, isRelative: s.isRelative, fontSize: s.fontSize'''
)

# 2. Update loadStickersState to migrate absolute stickers to relative
migrate_logic = '''
                editorStickers.forEach(s => {
                    if (!s.isRelative) {
                        if (s.start !== undefined) s.start = absToRel(s.start);
                        else s.start = 0;
                        if (s.end !== undefined) s.end = absToRel(s.end);
                        else s.end = (s.duration || 5.0);
                        s.isRelative = true;
                    }
                    if (s.type === 'video') {
'''
text = text.replace('''
                editorStickers.forEach(s => {
                    if (s.type === 'video') {''', migrate_logic)

migrate_logic2 = '''
                for(let s of parsed) {
                    if (!s.isRelative) {
                        if (s.start !== undefined) s.start = absToRel(s.start);
                        else s.start = 0;
                        if (s.end !== undefined) s.end = absToRel(s.end);
                        else s.end = s.start + (s.duration || 5.0);
                        s.isRelative = true;
                    }
                    let stStart = s.start;
                    let stEnd = s.end;
                    let vidEl = null, imgEl = null;'''
text = text.replace('''
                for(let s of parsed) {
                    let vidEl = null, imgEl = null;
                    
                    let stStart = currentStickerStart;
                    let defaultDur = s.duration || 5.0; 
                    if (s.duration === undefined && s.end !== undefined && s.start !== undefined) {
                        defaultDur = s.end - s.start;
                    }
                    let stEnd = Math.min(currentClip.end, stStart + defaultDur);
                    currentStickerStart = stEnd;''', migrate_logic2)

with open('templates/index.html', 'w', encoding='utf-8') as f:
    f.write(text)
print("Done step 1 and 2")
