with open('backend.py', 'r', encoding='utf-8') as f:
    text = f.read()

target = '''        # Procesar Sonidos
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

replacement = '''        # Procesar Sonidos
        current_a = "a_concat_base"
        sound_amix_inputs = [f"[{current_a}]"]
        for i, snd in enumerate(sound_inputs):
            snd_start = snd['start']
            
            delay_ms = int(snd_start * 1000)
            filter_parts.append(f"[{snd['idx']}:a]adelay={delay_ms}|{delay_ms}[a_snd_{i}]")
            sound_amix_inputs.append(f"[a_snd_{i}]")'''

if target in text:
    text = text.replace(target, replacement)
    with open('backend.py', 'w', encoding='utf-8') as f:
        f.write(text)
    print("Sounds backend updated")
else:
    print("Sounds target not found")
