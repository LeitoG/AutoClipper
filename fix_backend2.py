with open('backend.py', 'r', encoding='utf-8') as f:
    text = f.read()

target2 = '''            # Map start and end using intersection for duplicated scenes
            st_start = st['start']
            st_end = st['end']
            
            enable_exprs = []
            rel_offset = 0.0
            first_s_rel = None
            
            for sc in req.scenes:
                i_start = max(st_start, sc['start'])
                i_end = min(st_end, sc['end'])
                if i_start < i_end:
                    s_rel = rel_offset + (i_start - sc['start'])
                    e_rel = rel_offset + (i_end - sc['start'])
                    enable_exprs.append(f"between(t,{s_rel},{e_rel})")
                    if first_s_rel is None: first_s_rel = s_rel
                rel_offset += (sc['end'] - sc['start'])
                
            if not enable_exprs:
                continue
                
            enable_expr = "enable='" + "+".join(enable_exprs) + "'"'''

replacement2 = '''            st_start = st['start']
            st_end = st['end']
            
            enable_expr = f"enable='between(t,{st_start},{st_end})'"
            first_s_rel = st_start'''

if target2 in text:
    text = text.replace(target2, replacement2)
else:
    print("Target 2 not found")

with open('backend.py', 'w', encoding='utf-8') as f:
    f.write(text)
print("Part 2 done")
