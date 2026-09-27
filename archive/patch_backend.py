import os
import re
import base64

backend_path = r"C:\Users\leone\Desktop\OBS Grabaciones\Exports\Complete Games\backend.py"
with open(backend_path, "r", encoding="utf-8") as f:
    code = f.read()

# Buscamos la función export_clip
start_idx = code.find('def export_clip(req: ExportRequest):')
end_idx = code.find('@app.post("/transcribe")', start_idx)

new_func = """def export_clip(req: ExportRequest):
    try:
        video_path = os.path.join(VIDEO_DIR, req.video_name)
        if not os.path.exists(video_path):
            return {"status": "error", "message": f"Video fuente no encontrado: {video_path}"}
            
        out_file = os.path.join(EXPORTS_DIR, f"{req.clip_id}_render.mp4")
        
        # 1. Generar Subtítulos Dinámicos (.ass)
        ass_path = os.path.join(ASS_DIR, f"subs_{req.clip_id}_auto.ass")
        def format_time(ms):
            h = ms // 360000
            m = (ms % 360000) // 6000
            s = (ms % 6000) // 100
            cs = ms % 100
            return f"{h}:{m:02d}:{s:02d}.{cs:02d}"

        with open(ass_path, "w", encoding="utf-8") as f:
            f.write("[Script Info]\\nScriptType: v4.00+\\nPlayResX: 1080\\nPlayResY: 1920\\n\\n[V4+ Styles]\\nFormat: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\\n")
            
            raw_color = req.subtitle_style.get("color", "&H00FF33CC&")
            s_color = raw_color[:-1] if raw_color.endswith("&") else raw_color
            s_font = req.subtitle_style.get("font", "Arial Black")
            s_anim = req.subtitle_style.get("anim", "bounce")
            s_size = req.subtitle_style.get("size", "95")
            
            f.write(f"Style: Default,{s_font},{s_size},{s_color},&H000000FF,&H00000000,&H00000000,-1,0,0,0,100,100,0,0,1,12,0,5,10,10,10,1\\n\\n[Events]\\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\\n")
            
            for w in req.words:
                s_ms = int((w["start"] - req.start) * 1000)
                e_ms = int((w["end"] - req.start) * 1000)
                
                # Desplazar tiempos si hay gancho (1.5s = 1500ms)
                if req.hook:
                    s_ms += 1500
                    e_ms += 1500
                    
                active_scene = None
                for sc in req.scenes:
                    if w['start'] >= sc['start'] and w['start'] < sc['end']:
                        active_scene = sc
                        break
                if not active_scene:
                    active_scene = req.scenes[-1]
                
                cc = active_scene['cropState']['subs']
                sx, sy, sw, sh = cc['x'], cc['y'], cc['w'], cc['h']
                draw_x = int((sx + sw/2) * (1080/1920))
                draw_y = int((sy + sh/2) * (1920/1080))
                
                anim_tag = ""
                if s_anim == "bounce":
                    anim_tag = r"{\\fscx0\\fscy0\\t(0,100,\\fscx120\\fscy120)\\t(100,200,\\fscx100\\fscy100)}"
                elif s_anim == "pop":
                    anim_tag = r"{\\fscx50\\fscy50\\t(0,150,\\fscx100\\fscy100)}"
                    
                f.write(f"Dialogue: 0,{format_time(s_ms)},{format_time(e_ms)},Default,,0,0,0,,{{\\\\pos({draw_x},{draw_y})}}{anim_tag}{w['text']}\\n")

        ass_ff = ass_path.replace("\\\\", "/").replace(":", "\\\\:")
        
        # 2. Archivos e Inputs de FFmpeg
        inputs_args = ["-i", video_path]
        filter_parts = []
        input_idx = 1
        
        # Guardar Outro si existe
        outro_idx = -1
        if req.outro and "dataUrl" in req.outro:
            b64_data = req.outro["dataUrl"].split(",")[1]
            outro_path = os.path.join(TEMP_CLIPS_DIR, f"outro_{req.clip_id}.png")
            with open(outro_path, "wb") as f:
                f.write(base64.b64decode(b64_data))
            inputs_args.extend(["-i", outro_path])
            outro_idx = input_idx
            input_idx += 1
            
        # Guardar Stickers si existen
        sticker_inputs = []
        if req.stickers:
            for i, st in enumerate(req.stickers):
                b64_data = st["dataUrl"].split(",")[1]
                st_path = os.path.join(TEMP_CLIPS_DIR, f"st_{req.clip_id}_{i}.png")
                with open(st_path, "wb") as f:
                    f.write(base64.b64decode(b64_data))
                inputs_args.extend(["-i", st_path])
                sticker_inputs.append({"idx": input_idx, "x": st["x"], "y": st["y"], "w": st["w"], "h": st["h"]})
                input_idx += 1
        
        def format_scene(s_input, scene, out_name):
            if scene['template'] == 'face_game':
                cf = scene['cropState']['face']
                cg = scene['cropState']['game']
                if req.fit_mode == 'cover':
                    filter_parts.append(f"[{s_input}]split=2[vf_{out_name}][vg_{out_name}]")
                    filter_parts.append(f"[vf_{out_name}]crop={int(cf['w'])}:{int(cf['h'])}:{int(cf['x'])}:{int(cf['y'])},scale=1080:960:force_original_aspect_ratio=increase,crop=1080:960[face_{out_name}]")
                    filter_parts.append(f"[vg_{out_name}]crop={int(cg['w'])}:{int(cg['h'])}:{int(cg['x'])}:{int(cg['y'])},scale=1080:960:force_original_aspect_ratio=increase,crop=1080:960[game_{out_name}]")
                else:
                    filter_parts.append(f"[{s_input}]split=2[vf_{out_name}][vg_{out_name}]")
                    filter_parts.append(f"[vf_{out_name}]crop={int(cf['w'])}:{int(cf['h'])}:{int(cf['x'])}:{int(cf['y'])}[f_raw_{out_name}]")
                    filter_parts.append(f"[f_raw_{out_name}]split=2[f_bg_{out_name}][f_fg_{out_name}]")
                    filter_parts.append(f"[f_bg_{out_name}]scale=1080:960,boxblur=20:5,colorchannelmixer=rr=0.3:gg=0.3:bb=0.3[f_blur_{out_name}]")
                    filter_parts.append(f"[f_fg_{out_name}]scale=1080:960:force_original_aspect_ratio=decrease[f_scale_{out_name}]")
                    filter_parts.append(f"[f_blur_{out_name}][f_scale_{out_name}]overlay=(W-w)/2:(H-h)/2[face_{out_name}]")
                    
                    filter_parts.append(f"[vg_{out_name}]crop={int(cg['w'])}:{int(cg['h'])}:{int(cg['x'])}:{int(cg['y'])}[g_raw_{out_name}]")
                    filter_parts.append(f"[g_raw_{out_name}]split=2[g_bg_{out_name}][g_fg_{out_name}]")
                    filter_parts.append(f"[g_bg_{out_name}]scale=1080:960,boxblur=20:5,colorchannelmixer=rr=0.3:gg=0.3:bb=0.3[g_blur_{out_name}]")
                    filter_parts.append(f"[g_fg_{out_name}]scale=1080:960:force_original_aspect_ratio=decrease[g_scale_{out_name}]")
                    filter_parts.append(f"[g_blur_{out_name}][g_scale_{out_name}]overlay=(W-w)/2:(H-h)/2[game_{out_name}]")
                filter_parts.append(f"[face_{out_name}][game_{out_name}]vstack=inputs=2[{out_name}]")
            else:
                cc = scene['cropState']['full']
                filter_parts.append(f"[{s_input}]crop={int(cc['w'])}:{int(cc['h'])}:{int(cc['x'])}:{int(cc['y'])},scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920[{out_name}]")

        # Generar Hook (Si existe)
        inputs_concat = []
        if req.hook:
            h_time = req.hook['time']
            h_text = req.hook['text'].replace("'", "\\\\'")
            filter_parts.append(f"[0:v]trim=start={h_time}:end={h_time+0.1},setpts=PTS-STARTPTS,loop=loop=45:size=1:start=0[hook_src]")
            # Formatear usando la primera escena
            format_scene("hook_src", req.scenes[0], "hook_fmt")
            # Dibujar caja y texto
            # Arial Black en Windows: C:/Windows/Fonts/ariblk.ttf
            font_path = "C\\\\:/Windows/Fonts/ariblk.ttf"
            filter_parts.append(f"[hook_fmt]drawbox=y=(ih-200)/2:color=black@0.7:width=iw:height=200:t=fill,drawtext=fontfile='{font_path}':text='{h_text}':fontcolor=yellow:fontsize=80:x=(w-text_w)/2:y=(h-text_h)/2:shadowcolor=black:shadowx=3:shadowy=3[out_hook]")
            inputs_concat.append("[out_hook]")

        # Generar Escenas Normales
        for i, scene in enumerate(req.scenes):
            s_start = scene['start']
            s_end = scene['end']
            filter_parts.append(f"[0:v]trim=start={s_start}:end={s_end},setpts=PTS-STARTPTS[v_s{i}]")
            format_scene(f"v_s{i}", scene, f"out_{i}")
            inputs_concat.append(f"[out_{i}]")
            
        concat_str = "".join(inputs_concat) + f"concat=n={len(inputs_concat)}:v=1:a=0[v_concat]"
        filter_parts.append(concat_str)
        
        # Aplicar Subtítulos
        filter_parts.append(f"[v_concat]subtitles='{ass_ff}'[v_subs]")
        
        current_v = "v_subs"
        
        # Aplicar Stickers
        for i, st in enumerate(sticker_inputs):
            # Scale sticker to relative sizes
            scale_w = int(st['w'] * (1080/1920))
            scale_h = int(st['h'] * (1920/1080))
            pos_x = int(st['x'] * (1080/1920))
            pos_y = int(st['y'] * (1920/1080))
            filter_parts.append(f"[{st['idx']}:v]scale={scale_w}:{scale_h}[st_{i}]")
            filter_parts.append(f"[{current_v}][st_{i}]overlay={pos_x}:{pos_y}[v_st_{i}]")
            current_v = f"v_st_{i}"
            
        # Aplicar Outro (Imagen final de 5s)
        if outro_idx != -1:
            # Escalar Outro con Blur padding para 9:16
            filter_parts.append(f"[{outro_idx}:v]scale=1080:1920:force_original_aspect_ratio=decrease[out_fg]")
            filter_parts.append(f"[{outro_idx}:v]scale=1080:1920,boxblur=20:5,colorchannelmixer=rr=0.3:gg=0.3:bb=0.3[out_bg]")
            filter_parts.append(f"[out_bg][out_fg]overlay=(W-w)/2:(H-h)/2[outro_fmt]")
            # Loop por 5 segundos (30fps = 150 frames aprox)
            filter_parts.append(f"[outro_fmt]loop=loop=150:size=1:start=0,setpts=N/FRAME_RATE/TB[outro_vid]")
            # Concatenar video principal con outro
            filter_parts.append(f"[{current_v}][outro_vid]concat=n=2:v=1:a=0[v_final]")
            current_v = "v_final"
            
        filter_parts.append(f"[{current_v}]copy[v_out]")
        filter_complex = ";".join(filter_parts)
        
        total_dur = req.end - req.start
        if req.hook: total_dur += 1.5
        if outro_idx != -1: total_dur += 5.0
        
        cmd = [FFMPEG_BIN, "-y"] + inputs_args + [
            "-filter_complex", filter_complex,
            "-map", "[v_out]", "-map", "0:a",
            "-c:v", "libx264", "-preset", "ultrafast", "-crf", "23",
            "-c:a", "aac", out_file
        ]
        
        threading.Thread(target=run_ffmpeg, args=(cmd, req.clip_id, total_dur)).start()
        
        return {"status": "success", "output": out_file, "message": "Render iniciado en segundo plano."}
    except Exception as e:
        return {"status": "error", "message": str(e), "trace": traceback.format_exc()}

"""

code = code[:start_idx] + new_func + code[end_idx:]

with open(backend_path, "w", encoding="utf-8") as f:
    f.write(code)
print("Backend updated successfully!")
