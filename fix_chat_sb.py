import re

with open('backend.py', 'r', encoding='utf-8') as f:
    text = f.read()

target = r"        # Procesar chat \(TwitchDownloader JSON\) si existe.*?# Procesar marcadores de Streamdeck"

replacement = r'''        # Procesar chat (Streamer.bot o TwitchDownloader)
        # 1. TwitchDownloader JSON
        chat_file = video_path.rsplit('.', 1)[0] + '.json'
        if not os.path.exists(chat_file):
            chat_file = video_path.rsplit('.', 1)[0] + '_chat.json'
            
        if os.path.exists(chat_file):
            print(f"Archivo de chat encontrado: {chat_file}")
            try:
                with open(chat_file, 'r', encoding='utf-8') as f:
                    chat_data = json.load(f)
                
                if 'comments' in chat_data:
                    from collections import defaultdict
                    buckets = defaultdict(list)
                    for c in chat_data['comments']:
                        sec = c.get('content_offset_seconds', 0)
                        body = c.get('message', {}).get('body', '').lower()
                        bucket_idx = int(sec / 30)
                        buckets[bucket_idx].append(body)
                    
                    hot_keywords = ['lul', 'jaja', 'kekw', 'omegalul', 'pog', 'f', 'xd']
                    for b_idx, msgs in buckets.items():
                        hot_count = sum(1 for m in msgs if any(k in m for k in hot_keywords))
                        if hot_count >= 5 or (len(msgs) >= 15 and hot_count >= 3):
                            peak_sec = b_idx * 30 + 15
                            c = {
                                "start": max(0, peak_sec - 30),
                                "end": peak_sec + 30,
                                "reason": "Pico de reacciones en el Chat (JSON)",
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
                print(f"Error procesando chat JSON: {e}")

        # 2. Streamer.bot TXT log
        sb_chat_file = os.path.join(DB_DIR, 'chat.txt')
        if os.path.exists(sb_chat_file):
            try:
                stat = os.stat(video_path)
                import datetime
                video_start_time = datetime.datetime.fromtimestamp(stat.st_ctime)
                video_end_time = datetime.datetime.fromtimestamp(stat.st_mtime)
                
                with open(sb_chat_file, 'r', encoding='utf-8') as f:
                    chat_lines = f.readlines()
                    
                from collections import defaultdict
                buckets = defaultdict(list)
                
                for line in chat_lines:
                    line = line.strip()
                    if not line or '|' not in line: continue
                    time_str, body = line.split('|', 1)
                    body = body.lower()
                    
                    try:
                        # Parsear formato de Streamer.bot "YYYY-MM-DD HH:MM:SS"
                        msg_time = datetime.datetime.strptime(time_str.strip(), '%Y-%m-%d %H:%M:%S')
                        if video_start_time <= msg_time <= video_end_time:
                            rel_seconds = (msg_time - video_start_time).total_seconds()
                            bucket_idx = int(rel_seconds / 30)
                            buckets[bucket_idx].append(body)
                    except:
                        pass
                        
                hot_keywords = ['lul', 'jaja', 'kekw', 'omegalul', 'pog', 'f', 'xd']
                for b_idx, msgs in buckets.items():
                    hot_count = sum(1 for m in msgs if any(k in m for k in hot_keywords))
                    if hot_count >= 3 or (len(msgs) >= 10 and hot_count >= 2):
                        peak_sec = b_idx * 30 + 15
                        c = {
                            "start": max(0, peak_sec - 30),
                            "end": peak_sec + 30,
                            "reason": "Pico de reacciones en el Chat (Streamer.bot)",
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
                print(f"Error procesando chat de Streamer.bot: {e}")

        # Procesar marcadores de Streamdeck'''

new_text = re.sub(target, replacement, text, flags=re.DOTALL)
if new_text != text:
    with open('backend.py', 'w', encoding='utf-8') as f:
        f.write(new_text)
    print("Replaced!")
else:
    print("Not replaced.")
