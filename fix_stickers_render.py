with open('templates/index.html', 'r', encoding='utf-8') as f:
    text = f.read()

import re

target = '''                        if (st.start === undefined) st.start = currentClip.start;
                        if (st.end === undefined) st.end = currentClip.end;
                        
                        let relOffset = 0;
                        let firstRel = null;
                        let lastRel = null;
                        
                        editorScenes.forEach(sc => {
                            let i_start = Math.max(st.start, sc.start);
                            let i_end = Math.min(st.end, sc.end);
                            if (i_start < i_end) {
                                const s_rel = relOffset + (i_start - sc.start);
                                const e_rel = relOffset + (i_end - sc.start);
                                if (firstRel === null) firstRel = s_rel;
                                lastRel = e_rel;
                            }
                            relOffset += (sc.end - sc.start);
                        });
                        
                        if (firstRel !== null && lastRel !== null) {
                            const sPerc = (firstRel / totalDur) * 100;
                            const wPerc = ((lastRel - firstRel) / totalDur) * 100;'''

replacement = '''                        if (st.start === undefined) st.start = 0;
                        if (st.end === undefined) st.end = totalDur;
                        
                        let firstRel = st.start;
                        let lastRel = st.end;
                        
                        if (firstRel !== null && lastRel !== null) {
                            const sPerc = (firstRel / totalDur) * 100;
                            const wPerc = ((lastRel - firstRel) / totalDur) * 100;'''

if target in text:
    text = text.replace(target, replacement)
    with open('templates/index.html', 'w', encoding='utf-8') as f:
        f.write(text)
    print("Done step 4")
else:
    print("Target not found")
