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

st.set_page_config(page_title="Auto Clipper V6", layout="wide")

FFMPEG_BIN = r"C:\Users\leone\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1.1-full_build\bin\ffmpeg.exe"
ANALYSIS_FILE = r"C:\Users\leone\Desktop\OBS Grabaciones\Exports\Complete Games\analysis.json"
TEMP_CONFIG = r"C:\Users\leone\Desktop\OBS Grabaciones\Exports\Complete Games\temp_config.json"
VIDEO_DIR = r"D:\OBS Grabaciones Secondary Disk\OBS Videos\The Closing Shift\Test"

st.markdown("<h1 style='color: #FF4B4B;'>Auto Clipper V6 - Pipeline Integrado 🎬</h1>", unsafe_allow_html=True)

if st.button("🚨 PANIC BUTTON (Matar FFmpeg & Limpiar Temp) 🚨", type="primary"):
    killed = 0
    for proc in psutil.process_iter(['pid', 'name']):
        try:
            if 'ffmpeg' in proc.info['name'].lower():
                proc.kill()
                killed += 1
        except:
            pass
    if os.path.exists(TEMP_CONFIG): os.remove(TEMP_CONFIG)
    st.session_state.clear()
    st.success(f"Se mataron {killed} procesos. Limpieza lista.")
    st.rerun()

# 1. Validación de Estado Crítica
if not os.path.exists(ANALYSIS_FILE):
    st.error("❌ ERROR CRÍTICO: No se encontró 'analysis.json'. La Fase de Análisis falló o aún no se ejecutó. Ejecuta el script de análisis primero.")
    st.stop()

with open(ANALYSIS_FILE, "r", encoding="utf-8") as f:
    analysis_data = json.load(f)

proposals = analysis_data.get("proposals", [])
video_file = analysis_data.get("video", "2026-06-14_21-09-06.mkv")
video_path = os.path.join(VIDEO_DIR, video_file)

if not os.path.exists(video_path):
    st.error(f"❌ ERROR: El video original '{video_path}' no existe en el disco. Verifica la ruta.")
    st.stop()

# Panel Lateral de Gestión de Clips
st.sidebar.header("📂 Gestión de Clips")
clip_options = {f"{c['id']} [{c.get('start',0)}s - {c.get('end',0)}s]": c for c in proposals}
selected_clip_name = st.sidebar.selectbox("Selecciona un Clip para editar:", list(clip_options.keys()))
selected_clip = clip_options[selected_clip_name]

# Lógica de Estado para refrescar UI al cambiar de clip
if 'current_clip_id' not in st.session_state or st.session_state.current_clip_id != selected_clip["id"]:
    st.session_state.current_clip_id = selected_clip["id"]
    st.session_state.template = "Template A (Split 50/50)"
    st.session_state.pop("canvas_key", None)
    st.rerun()

def convert_ass_to_vtt(ass_path, vtt_path):
    if not os.path.exists(ass_path): return
    lines = []
    with open(ass_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.startswith("Dialogue:"):
                parts = line.split(",", 9)
                if len(parts) >= 10:
                    st_time = parts[1].replace(".", ",")
                    en_time = parts[2].replace(".", ",")
                    if len(st_time.split(":")[0]) == 1: st_time = "0" + st_time
                    if len(en_time.split(":")[0]) == 1: en_time = "0" + en_time
                    
                    text = parts[9]
                    text = re.sub(r'\{.*?\}', '', text)
                    lines.append(f"{st_time}0 --> {en_time}0\n{text.strip()}\n")
                    
    with open(vtt_path, "w", encoding="utf-8") as f:
        f.write("WEBVTT\n\n")
        f.write("\n".join(lines))

ass_path = os.path.join(r"C:\Users\leone\Desktop\OBS Grabaciones\Exports\Clips_AI", f"subs_{selected_clip['id']}.ass")
if not os.path.exists(ass_path):
    # Fallback genérico si el usuario borró el subtítulo específico
    ass_path = r"C:\Users\leone\Desktop\OBS Grabaciones\Exports\Clips_AI\subs_clip_1.ass"
    
vtt_path = os.path.join(r"C:\Users\leone\Desktop\OBS Grabaciones\Exports\Clips_AI", f"subs_{selected_clip['id']}.vtt")

col1, col2 = st.columns([1, 1])

with col1:
    st.subheader(f"1. Reproductor en Vivo ({selected_clip['id']})")
    convert_ass_to_vtt(ass_path, vtt_path)
    
    st.video(video_path, subtitles=vtt_path if os.path.exists(vtt_path) else None, start_time=int(selected_clip.get('start', 0)))
    
    st.subheader("2. Edición de Subtítulos (.ass)")
    sub_content = ""
    if os.path.exists(ass_path):
        with open(ass_path, "r", encoding="utf-8") as f:
            sub_content = f.read()
    edited_subs = st.text_area("Ajusta el texto de Whisper aquí:", value=sub_content, height=250)

with col2:
    st.subheader("3. Canvas Visual Interactivo")
    new_template = st.radio("Plantilla:", ["Template A (Split 50/50)", "Template B (Inmersivo)"])
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
    cap.set(cv2.CAP_PROP_POS_FRAMES, int(selected_clip.get('start', 0)) * cap.get(cv2.CAP_PROP_FPS))
    ret, frame = cap.read()
    cap.release()
    
    if ret:
        bg_image = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        # REDIMENSIONAR LA IMAGEN PARA EVITAR EL ERROR "buffer too large" DE ASYNCIO
        bg_image = bg_image.resize((960, 540))
    else:
        bg_image = Image.new("RGB", (960, 540), (0,0,0))
        st.warning("⚠️ No se pudo extraer el frame con OpenCV.")
        
    st.info(f"🐛 Debug - Ruta de Video: {video_path}")
        
    canvas_result = st_canvas(
        fill_color="rgba(255, 165, 0, 0)", 
        stroke_width=2,
        background_image=bg_image,
        update_streamlit=True,
        height=540, 
        width=960,
        drawing_mode="transform",
        initial_drawing=initial_drawing,
        key=f"canvas_{st.session_state.template}_{st.session_state.current_clip_id}"
    )

st.markdown("---")
st.subheader("Flujo de Producción (Deploy)")
col_b1, col_b2 = st.columns([1, 1])

with col_b1:
    if st.button("💾 Guardar Configuración", type="secondary"):
        if canvas_result.json_data is not None and len(canvas_result.json_data["objects"]) >= 2:
            objects = canvas_result.json_data["objects"]
            face_obj, game_obj = objects[0], objects[1]
            
            config = {
                "clip_id": selected_clip["id"],
                "start": selected_clip.get("start", 0),
                "end": selected_clip.get("end", 50),
                "template": st.session_state.template,
                "face_coords": {
                    "x": int(face_obj["left"] * face_obj.get("scaleX", 1) * 2),
                    "y": int(face_obj["top"] * face_obj.get("scaleY", 1) * 2),
                    "w": int(face_obj["width"] * face_obj.get("scaleX", 1) * 2),
                    "h": int(face_obj["height"] * face_obj.get("scaleY", 1) * 2),
                },
                "game_coords": {
                    "x": int(game_obj["left"] * game_obj.get("scaleX", 1) * 2),
                    "y": int(game_obj["top"] * game_obj.get("scaleY", 1) * 2),
                    "w": int(game_obj["width"] * game_obj.get("scaleX", 1) * 2),
                    "h": int(game_obj["height"] * game_obj.get("scaleY", 1) * 2),
                }
            }
            with open(TEMP_CONFIG, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=4)
                
            if edited_subs != sub_content and os.path.exists(ass_path):
                with open(ass_path, "w", encoding="utf-8") as f:
                    f.write(edited_subs)
                    
            st.success("✅ Coordenadas y Textos guardados. Listo para Deploy.")
        else:
            st.error("Asegúrate de no borrar los recuadros base.")

with col_b2:
    if st.button("🚀 DEPLOY", type="primary"):
        if not os.path.exists(TEMP_CONFIG):
            st.error("❌ Primero debes 'Guardar Configuración'.")
        else:
            with open(TEMP_CONFIG, "r", encoding="utf-8") as f:
                cfg = json.load(f)
                
            ass_ff = ass_path.replace("\\", "/")
            out_file = os.path.join(r"C:\Users\leone\Desktop\OBS Grabaciones\Exports\Clips_AI", f"Deploy_{cfg['clip_id']}.mp4")
            
            fx, fy, fw, fh = cfg["face_coords"]["x"], cfg["face_coords"]["y"], cfg["face_coords"]["w"], cfg["face_coords"]["h"]
            gx, gy, gw, gh = cfg["game_coords"]["x"], cfg["game_coords"]["y"], cfg["game_coords"]["w"], cfg["game_coords"]["h"]
            
            if "Template A" in cfg["template"]:
                filter_complex = f"[0:v]crop={fw}:{fh}:{fx}:{fy},scale=1080:960[top];[0:v]crop={gw}:{gh}:{gx}:{gy},scale=1080:960[bottom];[top][bottom]vstack=inputs=2[v_base];[v_base]subtitles='{ass_ff}'[v]"
            else:
                filter_complex = f"[0:v]crop={gw}:{gh}:{gx}:{gy},scale=1080:1920[game];[0:v]crop={fw}:{fh}:{fx}:{fy},scale=400:-1[face];[game][face]overlay=x=(W-w)/2:y=150[v_base];[v_base]subtitles='{ass_ff}'[v]"
                
            cmd = [
                FFMPEG_BIN, "-y", "-ss", str(cfg["start"]), "-t", str(cfg["end"] - cfg["start"]), "-i", video_path,
                "-filter_complex", filter_complex,
                "-map", "[v]", "-map", "0:a",
                "-c:v", "libx264", "-preset", "ultrafast", "-crf", "23",
                "-c:a", "aac", out_file
            ]
            st.info("Renderizando... (FFMPEG iniciado)")
            subprocess.Popen(cmd)
            st.success(f"¡Deploy iniciado en 2do plano! El archivo final estará en:")
            st.code(out_file)
