with open('backend.py', 'r', encoding='utf-8') as f:
    text = f.read()

# 1. Text ASS stickers
target1 = '''                        st_end = st.get('end', 0.0)
                        
                        rel_offset = 0.0
                        for sc in req.scenes:
                            i_start = max(st_start, sc['start'])
                            i_end = min(st_end, sc['end'])
                            if i_start < i_end:
                                s_rel = rel_offset + (i_start - sc['start'])
                                e_rel = rel_offset + (i_end - sc['start'])
                                
                                s_ms = int(s_rel * 1000)
                                e_ms = int(e_rel * 1000)
                                
                                def html_to_ass_color(hc):'''
replacement1 = '''                        st_end = st.get('end', 0.0)
                        
                        if True:
                                s_ms = int(st_start * 1000)
                                e_ms = int(st_end * 1000)
                                
                                def html_to_ass_color(hc):'''

text = text.replace(target1, replacement1)

target1_b = '''                                tag = f"{{{move_tag}\\c{c_ass}\\3c{sc_ass}\\bord4\\fn{s_font}\\fs60\\an5\\q1}}"
                                f.write(f"Dialogue: 2,{format_time(s_ms)},{format_time(e_ms)},Default,,{margin_l},{margin_r},0,,{tag}{st.get('text', '')}\\n")
                            rel_offset += (sc['end'] - sc['start'])

        ass_ff = ass_path.replace("\\\\", "/").replace(":", "\\\\:")'''

replacement1_b = '''                                tag = f"{{{move_tag}\\c{c_ass}\\3c{sc_ass}\\bord4\\fn{s_font}\\fs60\\an5\\q1}}"
                                f.write(f"Dialogue: 2,{format_time(s_ms)},{format_time(e_ms)},Default,,{margin_l},{margin_r},0,,{tag}{st.get('text', '')}\\n")

        ass_ff = ass_path.replace("\\\\", "/").replace(":", "\\\\:")'''

text = text.replace(target1_b, replacement1_b)

# 2. Video stickers
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
text = text.replace(target2, replacement2)


# 3. Sounds
target3 = '''        # Procesar Sonidos
        current_a = "a_concat_base"
        sound_amix_inputs = [f"[{current_a}]"]
        for i, snd in enumerate(sound_inputs):
            snd_start = snd['start']
            
            # Encontrar el inicio relativo en la timeline concatenada
            rel_offset = 0.0
            first_s_rel = None
            
            for sc in req.scenes:
                if sc['start'] <= snd_start <= sc['end']:
                    first_s_rel = rel_offset + (snd_start - sc['start'])
                    break
                rel_offset += (sc['end'] - sc['start'])
                
            if first_s_rel is not None:
                delay_ms = int(first_s_rel * 1000)
                filter_parts.append(f"[{snd['idx']}:a]adelay={delay_ms}|{delay_ms}[a_snd_{i}]")
                sound_amix_inputs.append(f"[a_snd_{i}]")'''

replacement3 = '''        # Procesar Sonidos
        current_a = "a_concat_base"
        sound_amix_inputs = [f"[{current_a}]"]
        for i, snd in enumerate(sound_inputs):
            snd_start = snd['start']
            
            delay_ms = int(snd_start * 1000)
            filter_parts.append(f"[{snd['idx']}:a]adelay={delay_ms}|{delay_ms}[a_snd_{i}]")
            sound_amix_inputs.append(f"[a_snd_{i}]")'''
text = text.replace(target3, replacement3)

with open('backend.py', 'w', encoding='utf-8') as f:
    f.write(text)
print("Done backend replace")
