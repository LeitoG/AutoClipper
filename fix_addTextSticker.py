with open('templates/index.html', 'r', encoding='utf-8') as f:
    text = f.read()

target = '''            let cTime = workspaceVideo.currentTime;
            if (cTime < currentClip.start) cTime = currentClip.start;
            if (cTime >= currentClip.end) cTime = currentClip.start;
            
            let stStart = cTime;
            let stEnd = relToAbs(absToRel(stStart) + 5);
            if (stEnd > currentClip.end) stEnd = currentClip.end;'''

replacement = '''            let cTime = workspaceVideo.currentTime;
            if (cTime < currentClip.start) cTime = currentClip.start;
            if (cTime >= currentClip.end) cTime = currentClip.start;
            
            let stStart = absToRel(cTime);
            let totalDur = getTimelineDuration();
            let stEnd = stStart + 5;
            if (stEnd > totalDur) stEnd = totalDur;'''

text = text.replace(target, replacement)

with open('templates/index.html', 'w', encoding='utf-8') as f:
    f.write(text)
print("addTextSticker fixed")
