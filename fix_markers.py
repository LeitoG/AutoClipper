import re

with open('backend.py', 'r', encoding='utf-8') as f:
    text = f.read()

target = r"        if range_end < 999999:\s*exclusion_zones\.append\(\(range_end, 999999\)\)"

replacement = '''        if range_end < 999999:
            exclusion_zones.append((range_end, 999999))
            
        # Procesar marcadores de Streamdeck
        import datetime
        markers_file = os.path.join(DB_DIR, 'markers.txt')
        if os.path.exists(markers_file):
            try:
                stat = os.stat(video_path)
                video_start_time = datetime.datetime.fromtimestamp(stat.st_ctime)
                video_end_time = datetime.datetime.fromtimestamp(stat.st_mtime)
                
                with open(markers_file, 'r', encoding='utf-8') as f:
                    markers_lines = f.readlines()
                
                remaining_markers = []
                for line in markers_lines:
                    line = line.strip()
                    if not line: continue
                    try:
                        marker_time = datetime.datetime.strptime(line, '%Y-%m-%d %H:%M:%S')
                        # Si el marcador esta dentro del periodo de grabacion
                        if video_start_time <= marker_time <= video_end_time:
                            rel_seconds = (marker_time - video_start_time).total_seconds()
                            c = {
                                "start": max(0, rel_seconds - 30),
                                "end": rel_seconds + 30,
                                "reason": "Marcador manual desde Streamdeck",
                                "virality_score": 100,
                                "transcript": "Marcador insertado manualmente durante la grabacion.",
                                "social_title": "Clip Manual (Streamdeck)",
                                "social_desc": "Clip marcado manualmente en vivo.",
                                "yt_title": "Clip Manual (Streamdeck)",
                                "yt_desc": "Clip marcado manualmente en vivo.",
                                "yt_tags": "Leito4Gaming, Clip"
                            }
                            incremental_save(c)
                            # Actualizar zonas de exclusion para que la IA no lo repita
                            exclusion_zones.append((c["start"], c["end"]))
                        else:
                            remaining_markers.append(line)
                    except:
                        remaining_markers.append(line)
                        
                # Opcional: sobreescribir el archivo de marcadores solo con los que no se usaron
                # (Para no procesarlos de nuevo en otros videos, aunque el check de tiempo ya los filtra)
            except Exception as e:
                print(f"Error procesando marcadores: {e}")'''

new_text = re.sub(target, replacement, text)
if new_text != text:
    with open('backend.py', 'w', encoding='utf-8') as f:
        f.write(new_text)
    print("Replaced!")
else:
    print("Not replaced.")
