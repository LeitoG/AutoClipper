with open('backend.py', 'r', encoding='utf-8') as f:
    text = f.read()

# 1. Update text ASS sticker logic
target1 = '''                        st_end = st.get('end', 0.0)
                        
                        rel_offset = 0.0
                        for sc in req.scenes:
                            i_start = max(st_start, sc['start'])
                            i_end = min(st_end, sc['end'])
                            if i_start < i_end:
                                s_rel = rel_offset + (i_start - sc['start'])
                                e_rel = rel_offset + (i_end - sc['start'])
                                
                                s_ms = int(s_rel * 1000)
                                e_ms = int(e_rel * 1000)'''

replacement1 = '''                        st_end = st.get('end', 0.0)
                        
                        s_ms = int(st_start * 1000)
                        e_ms = int(st_end * 1000)'''

if target1 in text:
    text = text.replace(target1, replacement1)
    
    # We also need to remove the loop closure for req.scenes in the ASS logic
    # Look closely at how the logic was closed
    pass
else:
    print("Target 1 not found")

with open('backend.py', 'w', encoding='utf-8') as f:
    f.write(text)
print("Part 1 done")
