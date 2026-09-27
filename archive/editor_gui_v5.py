import streamlit as st
import cv2
import psutil
import os
import subprocess
import json
from streamlit_drawable_canvas import st_canvas
from PIL import Image
import re
import base64
from io import BytesIO
import streamlit.elements.image as st_image

# Monkey patch para compatibilidad entre versiones nuevas de Streamlit y drawable-canvas
if not hasattr(st_image, 'image_to_url'):
    def image_to_url(image, width, clamp, channels, output_format, image_id, allow_emoji=False):
        buffered = BytesIO()
        image.save(buffered, format=output_format if output_format else "PNG")
        img_str = base64.b64encode(buffered.getvalue()).decode()
        return f"data:image/png;base64,{img_str}"
    st_image.image_to_url = image_to_url


st.set_page_config(page_title="Auto Clipper V5", layout="wide")

FFMPEG_BIN = r"C:\Users\leone\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1.1-full_build\bin\ffmpeg.exe"

def panic_kill():
    killed = 0
    for proc in psutil.process_iter(['pid', 'name']):
        try:
            if 'ffmpeg' in proc.info['name'].lower():
                proc.kill()
                killed += 1
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
    st.session_state.clear()
    return killed

st.markdown("<h1 style='color: #FF4B4B;'>Auto Clipper V5 - Interactividad Total 🕹️</h1>", unsafe_allow_html=True)

if st.button("🚨 PANIC BUTTON (Matar FFmpeg & Reset) 🚨", type="primary"):
    k = panic_kill()
    st.success(f"Se mataron {k} procesos FFmpeg zombie. Estado de sesión reiniciado.")

def convert_ass_to_vtt(ass_path, vtt_path):
    if not os.path.exists(ass_path): return
    lines = []
    with open(ass_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.startswith("Dialogue:"):
                parts = line.split(",", 9)
                if len(parts) >= 10:
                    start_time = parts[1].replace(".", ",")
                    end_time = parts[2].replace(".", ",")
                    if len(start_time.split(":")[0]) == 1: start_time = "0" + start_time
                    if len(end_time.split(":")[0]) == 1: end_time = "0" + end_time
                    
                    text = parts[9]
                    text = re.sub(r'\{.*?\}', '', text)
                    lines.append(f"{start_time}0 --> {end_time}0\n{text.strip()}\n")
                    
    with open(vtt_path, "w", encoding="utf-8") as f:
        f.write("WEBVTT\n\n")
        f.write("\n".join(lines))

col1, col2 = st.columns([1, 1])

if 'template' not in st.session_state:
    st.session_state.template = "Template A (Split 50/50)"
    
video_path = r"D:\OBS Grabaciones Secondary Disk\OBS Videos\The Closing Shift\Test\2026-06-14_21-09-06.mkv"
ass_path = r"C:\Users\leone\Desktop\OBS Grabaciones\Exports\Clips_AI\subs_clip_1.ass"
vtt_path = r"C:\Users\leone\Desktop\OBS Grabaciones\Exports\Clips_AI\subs_clip_1.vtt"

with col1:
    st.subheader("1. Reproductor en Tiempo Real")
    convert_ass_to_vtt(ass_path, vtt_path)
    if os.path.exists(video_path):
        st.video(video_path, subtitles=vtt_path if os.path.exists(vtt_path) else None)
        
    st.subheader("2. Sincronización de Texto (.ass)")
    if os.path.exists(ass_path):
        with open(ass_path, "r", encoding="utf-8") as f:
            sub_content = f.read()
    else:
        sub_content = ""
        
    edited_subs = st.text_area("Modifica errores del audio aquí:", value=sub_content, height=250)
    if edited_subs != sub_content and os.path.exists(ass_path):
        with open(ass_path, "w", encoding="utf-8") as f:
            f.write(edited_subs)
        convert_ass_to_vtt(ass_path, vtt_path)
        st.rerun()

with col2:
    st.subheader("3. Canvas Visual Interactivo (Drag & Drop)")
    new_template = st.radio("Plantilla Dinámica:", ["Template A (Split 50/50)", "Template B (Inmersivo)", "Template C (Personalizado)"])
    
    if new_template != st.session_state.template:
        st.session_state.template = new_template
        st.session_state.pop("canvas_key", None)
        st.rerun()
        
    if "Template A" in st.session_state.template:
        objs = [
            {"type": "rect", "left": 750, "top": 300, "width": 210, "height": 240, "fill": "rgba(0,0,255,0.4)", "stroke": "blue", "strokeWidth": 2},
            {"type": "rect", "left": 210, "top": 0, "width": 540, "height": 540, "fill": "rgba(255,0,0,0.4)", "stroke": "red", "strokeWidth": 2}
        ]
    else:
        objs = [
            {"type": "rect", "left": 750, "top": 300, "width": 210, "height": 240, "fill": "rgba(0,0,255,0.4)", "stroke": "blue", "strokeWidth": 2},
            {"type": "rect", "left": 300, "top": 0, "width": 303, "height": 540, "fill": "rgba(255,0,0,0.4)", "stroke": "red", "strokeWidth": 2}
        ]
        
    initial_drawing = {"version": "4.4.0", "objects": objs}
    
    cap = cv2.VideoCapture(video_path)
    cap.set(cv2.CAP_PROP_POS_FRAMES, 15 * cap.get(cv2.CAP_PROP_FPS))
    ret, frame = cap.read()
    cap.release()
    
    if ret:
        bg_image = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
    else:
        bg_image = Image.new("RGB", (1920, 1080), (0,0,0))
        
    canvas_result = st_canvas(
        fill_color="rgba(255, 165, 0, 0)", 
        stroke_width=2,
        background_image=bg_image,
        update_streamlit=True,
        height=540, 
        width=960,
        drawing_mode="transform",
        initial_drawing=initial_drawing,
        key=f"canvas_{st.session_state.template}"
    )

st.markdown("---")
if st.button("Guardar Coordenadas de Canvas y Renderizar", type="primary"):
    if canvas_result.json_data is not None:
        objects = canvas_result.json_data["objects"]
        if len(objects) >= 2:
            face_obj = objects[0]
            game_obj = objects[1]
            
            fx = int(face_obj["left"] * face_obj.get("scaleX", 1) * 2)
            fy = int(face_obj["top"] * face_obj.get("scaleY", 1) * 2)
            fw = int(face_obj["width"] * face_obj.get("scaleX", 1) * 2)
            fh = int(face_obj["height"] * face_obj.get("scaleY", 1) * 2)
            
            gx = int(game_obj["left"] * game_obj.get("scaleX", 1) * 2)
            gy = int(game_obj["top"] * game_obj.get("scaleY", 1) * 2)
            gw = int(game_obj["width"] * game_obj.get("scaleX", 1) * 2)
            gh = int(game_obj["height"] * game_obj.get("scaleY", 1) * 2)
            
            st.info(f"Geometría Capturada: Face({fw}x{fh} en {fx},{fy}), Game({gw}x{gh} en {gx},{gy})")
            
            ass_ff = ass_path.replace("\\", "/")
            out_file = os.path.join(os.path.dirname(ass_path), "Render_V5.mp4")
            
            if "Template A" in st.session_state.template:
                filter_complex = f"[0:v]crop={fw}:{fh}:{fx}:{fy},scale=1080:960[top];[0:v]crop={gw}:{gh}:{gx}:{gy},scale=1080:960[bottom];[top][bottom]vstack=inputs=2[v_base];[v_base]subtitles='{ass_ff}'[v]"
            else:
                filter_complex = f"[0:v]crop={gw}:{gh}:{gx}:{gy},scale=1080:1920[game];[0:v]crop={fw}:{fh}:{fx}:{fy},scale=400:-1[face];[game][face]overlay=x=(W-w)/2:y=150[v_base];[v_base]subtitles='{ass_ff}'[v]"
                
            cmd = [
                FFMPEG_BIN, "-y", "-ss", "0", "-t", "10", "-i", video_path,
                "-filter_complex", filter_complex,
                "-map", "[v]", "-map", "0:a",
                "-c:v", "libx264", "-preset", "ultrafast", "-crf", "23",
                "-c:a", "aac", out_file
            ]
            subprocess.Popen(cmd)
            st.success("Renderizando en segundo plano! Usa el Panic Button arriba si detectas un error.")
        else:
            st.error("Error: Modificaste o borraste los recuadros base.")
