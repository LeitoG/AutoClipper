with open('templates/index.html', 'r', encoding='utf-8') as f:
    text = f.read()

target_add_sound = '''                        start: currentClip ? currentClip.start : 0,
                        end: currentClip ? currentClip.start + 5 : 5, // Default 5s'''
replacement_add_sound = '''                        start: 0,
                        end: 5, // Default 5s
                        isRelative: true,'''
text = text.replace(target_add_sound, replacement_add_sound)

target_render_sound = '''                editorSounds.forEach(snd => {
                    if (cTime >= snd.start && cTime <= snd.end) {
                        const relativeTime = absToRel(cTime) - absToRel(snd.start);
                        if (snd.audioElement) {
                            if (Math.abs(snd.audioElement.currentTime - relativeTime) > 0.1) {
                                snd.audioElement.currentTime = relativeTime;
                            }'''
replacement_render_sound = '''                const relTime = absToRel(cTime);
                editorSounds.forEach(snd => {
                    if (relTime >= snd.start && relTime <= snd.end) {
                        const relativeTime = relTime - snd.start;
                        if (snd.audioElement) {
                            if (Math.abs(snd.audioElement.currentTime - relativeTime) > 0.1) {
                                snd.audioElement.currentTime = relativeTime;
                            }'''
text = text.replace(target_render_sound, replacement_render_sound)

target_migrate = '''            if (saved && saved !== '[]') {
                try {
                    editorSounds = JSON.parse(saved);
                    editorSounds.forEach(s => { s.audioElement = new Audio(s.url); });'''
replacement_migrate = '''            if (saved && saved !== '[]') {
                try {
                    editorSounds = JSON.parse(saved);
                    editorSounds.forEach(s => { 
                        if (!s.isRelative) {
                            if (s.start !== undefined) s.start = absToRel(s.start);
                            else s.start = 0;
                            if (s.end !== undefined) s.end = absToRel(s.end);
                            else s.end = 5.0;
                            s.isRelative = true;
                        }
                        s.audioElement = new Audio(s.url); 
                    });'''
text = text.replace(target_migrate, replacement_migrate)

target_save = '''            const data = editorSounds.map(s => ({
                id: s.id, name: s.name, server_path: s.server_path, url: s.url,
                start: s.start, end: s.end
            }));'''
replacement_save = '''            const data = editorSounds.map(s => ({
                id: s.id, name: s.name, server_path: s.server_path, url: s.url,
                start: s.start, end: s.end, isRelative: s.isRelative
            }));'''
text = text.replace(target_save, replacement_save)

with open('templates/index.html', 'w', encoding='utf-8') as f:
    f.write(text)
print("Sounds migrated")
