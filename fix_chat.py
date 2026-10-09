import re

with open('backend.py', 'r', encoding='utf-8') as f:
    text = f.read()

target = r"        # Procesar marcadores de Streamdeck"

replacement = r'''        # Procesar chat (TwitchDownloader JSON) si existe
        chat_file = video_path.rsplit('.', 1)[0] + '.json'
        if not os.path.exists(chat_file):
            chat_file = video_path.rsplit('.', 1)[0] + '_chat.json'
            
        if os.path.exists(chat_file):
            print(f"Archivo de chat encontrado: {chat_file}")
            try:
                with open(chat_file, 'r', encoding='utf-8') as f:
                    chat_data = json.load(f)
                
                # Buscar picos de actividad o risas
                if 'comments' in chat_data:
                    # Agrupar por ventanas de 30 segundos
                    from collections import defaultdict
                    buckets = defaultdict(list)
                    for c in chat_data['comments']:
                        sec = c.get('content_offset_seconds', 0)
                        body = c.get('message', {}).get('body', '').lower()
                        bucket_idx = int(sec / 30)
                        buckets[bucket_idx].append(body)
                    
                    # Detectar picos (ej: mas de 5 mensajes con LUL/JAJA en 30s)
                    hot_keywords = ['lul', 'jaja', 'kekw', 'omegalul', 'pog', 'f', 'xd']
                    for b_idx, msgs in buckets.items():
                        hot_count = sum(1 for m in msgs if any(k in m for k in hot_keywords))
                        # Si hay un pico de actividad de risas/reacciones
                        if hot_count >= 5 or (len(msgs) >= 15 and hot_count >= 3):
                            peak_sec = b_idx * 30 + 15 # Centro del bucket
                            c = {
                                "start": max(0, peak_sec - 30),
                                "end": peak_sec + 30,
                                "reason": "Pico de reacciones en el Chat",
                                "virality_score": 95,
                                "transcript": "El chat enloquecio de repente.",
                                "social_title": "Clip del Chat",
                                "social_desc": "El chat exploto en este momento.",
                                "yt_title": "Clip del Chat",
                                "yt_desc": "Reaccion del chat en vivo.",
                                "yt_tags": "Leito4Gaming, Clip, Twitch"
                            }
                            incremental_save(c)
                            exclusion_zones.append((c["start"], c["end"]))
            except Exception as e:
                print(f"Error procesando chat: {e}")

        # Procesar marcadores de Streamdeck'''

new_text = text.replace(target, replacement)
if new_text != text:
    with open('backend.py', 'w', encoding='utf-8') as f:
        f.write(new_text)
    print("Replaced chat logic!")
else:
    print("Not replaced chat logic.")
