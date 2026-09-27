import streamlit as st
import cv2
from PIL import Image, ImageDraw
import subprocess
import os

st.set_page_config(page_title="Auto Clipper GUI", layout="wide")

st.title("Auto Clipper V4 - Editor Visual 🎬")

FFMPEG_BIN = r"C:\Users\leone\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1.1-full_build\bin\ffmpeg.exe"

# Modulares FFMPEG Functions
def render_template_a(video_path, face_coords, game_coords, ass_path, output_path):
    fx, fy, fw, fh = face_coords
    gx, gy, gw, gh = game_coords
    ass_ff = ass_path.replace("\\", "/")
    
    filter_complex = (
        f"[0:v]crop={fw}:{fh}:{fx}:{fy},scale=1080:960[top];"
        f"[0:v]crop={gw}:{gh}:{gx}:{gy},scale=1080:960[bottom];"
        f"[top][bottom]vstack=inputs=2[stacked];"
        f"[stacked]subtitles='{ass_ff}',"
        f"drawtext=text='¡MIRA ESTO!':fontcolor=white:fontsize=120:x=(w-text_w)/2:y=800:enable='between(t,0,3)':box=1:boxcolor=magenta@0.8:boxborderw=20,"
        f"drawtext=text='@Leito4Gaming':fontcolor=white:fontsize=60:x=(w-text_w)/2:y=h-150:box=1:boxcolor=black@0.6:boxborderw=10[v]"
    )
    
    cmd = [
        FFMPEG_BIN, "-y", "-ss", "0", "-t", "50", "-i", video_path, 
        "-filter_complex", filter_complex, 
        "-map", "[v]", "-map", "0:a", 
        "-c:v", "libx264", "-preset", "ultrafast", "-crf", "23",
        "-c:a", "aac", output_path
    ]
    subprocess.run(cmd, check=True)

def render_template_b(video_path, face_coords, game_coords, ass_path, output_path):
    fx, fy, fw, fh = face_coords
    gx, gy, gw, gh = game_coords
    ass_ff = ass_path.replace("\\", "/")
    
    filter_complex = (
        f"[0:v]crop={gw}:{gh}:{gx}:{gy},scale=1080:1920[game];"
        f"[0:v]crop={fw}:{fh}:{fx}:{fy},scale=400:-1[face];"
        f"[game][face]overlay=x=(W-w)/2:y=150[stacked];"
        f"[stacked]subtitles='{ass_ff}',"
        f"drawtext=text='¡MIRA ESTO!':fontcolor=white:fontsize=120:x=(w-text_w)/2:y=800:enable='between(t,0,3)':box=1:boxcolor=magenta@0.8:boxborderw=20,"
        f"drawtext=text='@Leito4Gaming':fontcolor=white:fontsize=60:x=(w-text_w)/2:y=h-150:box=1:boxcolor=black@0.6:boxborderw=10[v]"
    )
    
    cmd = [
        FFMPEG_BIN, "-y", "-ss", "0", "-t", "50", "-i", video_path, 
        "-filter_complex", filter_complex, 
        "-map", "[v]", "-map", "0:a", 
        "-c:v", "libx264", "-preset", "ultrafast", "-crf", "23",
        "-c:a", "aac", output_path
    ]
    subprocess.run(cmd, check=True)


col1, col2, col3 = st.columns([1, 2, 1])

with col1:
    st.header("Configuración")
    video_path = st.text_input("Ruta del Video", value=r"D:\OBS Grabaciones Secondary Disk\OBS Videos\The Closing Shift\Test\2026-06-14_21-09-06.mkv")
    
    default_ass = os.path.join(r"C:\Users\leone\Desktop\OBS Grabaciones\Exports\Clips_AI", "subs_clip_1.ass")
    ass_path = st.text_input("Ruta del Subtítulo (.ass)", value=default_ass)
    
    template = st.radio("Seleccionar Template", ["Template A (Split)", "Template B (Overlay)"])
    start_time = st.number_input("Previsualizar Segundo", min_value=0, value=15)

with col3:
    st.header("Sliders de Recorte")
    st.subheader("Facecam (Azul)")
    face_x = st.slider("Face X", 0, 1920, 1500)
    face_y = st.slider("Face Y", 0, 1080, 600)
    face_w = st.slider("Face Ancho", 100, 1920, 420)
    face_h = st.slider("Face Alto", 100, 1080, 480)
    
    st.subheader("Gameplay (Rojo)")
    game_x = st.slider("Game X", 0, 1920, 420)
    game_y = st.slider("Game Y", 0, 1080, 0)
    game_w = st.slider("Game Ancho", 100, 1920, 1080)
    game_h = st.slider("Game Alto", 100, 1080, 1080)

with col2:
    st.header("Canvas Visual")
    if os.path.exists(video_path):
        cap = cv2.VideoCapture(video_path)
        fps = cap.get(cv2.CAP_PROP_FPS)
        cap.set(cv2.CAP_PROP_POS_FRAMES, int(start_time * fps))
        ret, frame = cap.read()
        cap.release()
        
        if ret:
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            img = Image.fromarray(frame_rgb).convert("RGBA")
            overlay = Image.new("RGBA", img.size, (0,0,0,0))
            draw = ImageDraw.Draw(overlay)
            
            # Draw rectangles with semi-transparent fill
            draw.rectangle(((face_x, face_y), (face_x+face_w, face_y+face_h)), fill=(0, 0, 255, 80), outline=(0, 0, 255, 255), width=3)
            draw.rectangle(((game_x, game_y), (game_x+game_w, game_y+game_h)), fill=(255, 0, 0, 80), outline=(255, 0, 0, 255), width=3)
            
            final_img = Image.alpha_composite(img, overlay)
            st.image(final_img, use_container_width=True)
        else:
            st.error("Frame no encontrado.")

st.markdown("---")
st.header("Editor de Subtítulos (.ass)")
sub_content = ""
if os.path.exists(ass_path):
    with open(ass_path, "r", encoding="utf-8") as f:
        sub_content = f.read()

edited_subs = st.text_area("Contenido .ass", value=sub_content, height=300)

if st.button("Guardar y Renderizar", type="primary"):
    if os.path.exists(ass_path) and edited_subs != sub_content:
        with open(ass_path, "w", encoding="utf-8") as f:
            f.write(edited_subs)
        st.success("Subtítulos actualizados correctamente.")
        
    out_dir = os.path.dirname(ass_path)
    final_mp4 = os.path.join(out_dir, "Render_Streamlit_V4.mp4")
    
    with st.spinner("Renderizando con FFMPEG C++ Engine..."):
        try:
            if "Template A" in template:
                render_template_a(video_path, (face_x, face_y, face_w, face_h), (game_x, game_y, game_w, game_h), ass_path, final_mp4)
            else:
                render_template_b(video_path, (face_x, face_y, face_w, face_h), (game_x, game_y, game_w, game_h), ass_path, final_mp4)
            st.success(f"Video exportado con éxito en: {final_mp4}")
        except Exception as e:
            st.error(f"Error al renderizar: {e}")
