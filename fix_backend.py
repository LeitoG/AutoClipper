import re

with open('backend.py', 'r', encoding='utf-8') as f:
    text = f.read()

target = '''        # Recopilar zonas a excluir (clips ya generados o completados)
        exclusion_zones = []'''

replacement = '''        def parse_time(t_str, default):
            if not t_str: return default
            parts = t_str.split(':')
            try:
                if len(parts) == 3:
                    return int(parts[0])*3600 + int(parts[1])*60 + int(parts[2])
                elif len(parts) == 2:
                    return int(parts[0])*60 + int(parts[1])
                elif len(parts) == 1:
                    return int(parts[0])
            except:
                return default
            return default
            
        range_start = parse_time(req.start_time_str, 0)
        range_end = parse_time(req.end_time_str, 999999)
        
        # Recopilar zonas a excluir (clips ya generados o completados)
        exclusion_zones = []
        if range_start > 0:
            exclusion_zones.append((0, range_start))
        if range_end < 999999:
            exclusion_zones.append((range_end, 999999))'''

new_text = text.replace(target, replacement)
if new_text != text:
    with open('backend.py', 'w', encoding='utf-8') as f:
        f.write(new_text)
    print("Replaced!")
else:
    print("Not replaced.")
