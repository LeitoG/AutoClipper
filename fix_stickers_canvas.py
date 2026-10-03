with open('templates/index.html', 'r', encoding='utf-8') as f:
    text = f.read()

target = '''            if (currentClip) {
                const cTime = workspaceVideo.currentTime;
                editorStickers.forEach(st => {
                    if (cTime >= st.start && cTime <= st.end) {
                        const drawW = st.w;
                        const drawH = st.h;
                        const drawX = st.x;
                        const drawY = st.y;
                        
                        if (st.type === 'video' && st.videoElement) {
                            const relativeTime = absToRel(cTime) - absToRel(st.start);
                            if (Math.abs(st.videoElement.currentTime - relativeTime) > 0.1) {
                                st.videoElement.currentTime = relativeTime;
                            }'''

replacement = '''            if (currentClip) {
                const cTime = workspaceVideo.currentTime;
                const relTime = absToRel(cTime);
                editorStickers.forEach(st => {
                    if (relTime >= st.start && relTime <= st.end) {
                        const drawW = st.w;
                        const drawH = st.h;
                        const drawX = st.x;
                        const drawY = st.y;
                        
                        if (st.type === 'video' && st.videoElement) {
                            const relativeTime = relTime - st.start;
                            if (Math.abs(st.videoElement.currentTime - relativeTime) > 0.1) {
                                st.videoElement.currentTime = relativeTime;
                            }'''

if target in text:
    text = text.replace(target, replacement)
    with open('templates/index.html', 'w', encoding='utf-8') as f:
        f.write(text)
    print("Done step 6")
else:
    print("Target not found")
