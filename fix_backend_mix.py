with open('backend.py', 'r', encoding='utf-8') as f:
    text = f.read()

target = '''            export_track = getattr(req, "export_track", "mix")
            if export_track == "mix" and num_audio_streams > 1:
                mix_inputs = []
                for a_idx in range(num_audio_streams):
                    filter_parts.append(f"[0:a:{a_idx}]atrim=start={s_start:.6f}:end={s_end:.6f},asetpts=PTS-STARTPTS[a_s{i}_t{a_idx}]")
                    mix_inputs.append(f"[a_s{i}_t{a_idx}]")
                mix_str = "".join(mix_inputs)
                filter_parts.append(f"{mix_str}amix=inputs={num_audio_streams}:duration=longest:dropout_transition=0,volume={num_audio_streams}[a_s{i}]")
            else:
                try:
                    a_idx = int(export_track) - 1
                except:
                    a_idx = 0
                if a_idx >= num_audio_streams or a_idx < 0:
                    a_idx = 0
                filter_parts.append(f"[0:a:{a_idx}]atrim=start={s_start:.6f}:end={s_end:.6f},asetpts=PTS-STARTPTS[a_s{i}]")'''

replacement = '''            export_track = getattr(req, "export_track", "mix")
            if export_track == "mix" and num_audio_streams > 1:
                tv = req.track_voz - 1
                tj = req.track_juego - 1
                
                valid_tracks = []
                if 0 <= tv < num_audio_streams:
                    valid_tracks.append((tv, req.vol_voz))
                if 0 <= tj < num_audio_streams and tj != tv:
                    valid_tracks.append((tj, req.vol_juego))
                
                if not valid_tracks:
                    for a_idx in range(num_audio_streams):
                        valid_tracks.append((a_idx, 1.0))
                
                mix_inputs = []
                for idx_in_valid, (a_idx, vol) in enumerate(valid_tracks):
                    filter_parts.append(f"[0:a:{a_idx}]atrim=start={s_start:.6f}:end={s_end:.6f},asetpts=PTS-STARTPTS,volume={vol}[a_s{i}_t{a_idx}]")
                    mix_inputs.append(f"[a_s{i}_t{a_idx}]")
                
                mix_str = "".join(mix_inputs)
                num_valid = len(valid_tracks)
                if num_valid > 1:
                    filter_parts.append(f"{mix_str}amix=inputs={num_valid}:duration=longest:dropout_transition=0,volume={num_valid}[a_s{i}]")
                else:
                    filter_parts.append(f"{mix_str}anull[a_s{i}]")
            else:
                try:
                    a_idx = int(export_track) - 1
                except:
                    a_idx = 0
                if a_idx >= num_audio_streams or a_idx < 0:
                    a_idx = 0
                filter_parts.append(f"[0:a:{a_idx}]atrim=start={s_start:.6f}:end={s_end:.6f},asetpts=PTS-STARTPTS,volume={req.vol_voz}[a_s{i}]")'''

text = text.replace(target, replacement)

with open('backend.py', 'w', encoding='utf-8') as f:
    f.write(text)
print("Updated export_clip mixing logic")
