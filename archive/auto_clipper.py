import argparse
import os
import json
import whisper
import numpy as np
import cv2
import mediapipe as mp
import subprocess
from moviepy import AudioFileClip
from datetime import datetime

# Configuraciones de entorno
FFMPEG_BIN_PATH = r"C:\Users\leone\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1.1-full_build\bin"
os.environ["PATH"] = FFMPEG_BIN_PATH + os.pathsep + os.environ.get("PATH", "")

OUTPUT_DIR = r"C:\Users\leone\Desktop\OBS Grabaciones\Exports\Clips_AI"

def format_time_ass(seconds):
    hrs = int(seconds // 3600)
    mins = int((seconds % 3600) // 60)
    secs = seconds % 60
    return f"{hrs:d}:{mins:02d}:{secs:05.2f}"

def generate_ass(segments, output_path, start_offset, end_offset):
    lines = [
        "[Script Info]",
        "ScriptType: v4.00+",
        "PlayResX: 1080",
        "PlayResY: 1920",
        "",
        "[V4+ Styles]",
        "Format: Name, Fontname, Fontsize, PrimaryColour, OutlineColour, BackColour, Bold, Italic, Alignment, MarginV, Outline, Shadow",
        "Style: Default, Impact, 85, &H00FFFFFF, &H00000000, &H00000000, -1, 0, 2, 700, 6, 3",
        "",
        "[Events]",
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text"
    ]
    
    for segment in segments:
        words = segment.get("words", [])
        for i, w in enumerate(words):
            w_start = w["start"] - start_offset
            w_end = w["end"] - start_offset
            
            # Solo incluir palabras dentro del rango del clip de 55 segundos
            if w_end < 0 or w_start > (end_offset - start_offset):
                continue
                
            w_start = max(0, w_start)
            w_end = max(0, w_end)
            
            if i < len(words) - 1:
                next_start = words[i+1]["start"] - start_offset
                if next_start - w_end < 0.2:
                    w_end = next_start
            
            line_start = format_time_ass(w_start)
            line_end = format_time_ass(w_end)
            text = w["word"].strip().upper()
            
            anim = r"{\c&H00FF00FF&\fscx140\fscy140\t(0,80,\fscx100\fscy100)}"
            dialogue = f"Dialogue: 0,{line_start},{line_end},Default,,0,0,0,,{anim}{text}"
            lines.append(dialogue)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision as mp_vision
import urllib.request

def get_dynamic_facecam_crop(video_path):
    print("Iniciando escaneo de rostro con MediaPipe (Ultra preciso)...")
    
    model_path = os.path.join(OUTPUT_DIR, 'blaze_face_short_range.tflite')
    if not os.path.exists(model_path):
        print("Descargando modelo de IA facial...")
        urllib.request.urlretrieve('https://storage.googleapis.com/mediapipe-models/face_detector/blaze_face_short_range/float16/1/blaze_face_short_range.tflite', model_path)
        
    base_options = mp_python.BaseOptions(model_asset_path=model_path)
    options = mp_vision.FaceDetectorOptions(base_options=base_options, min_detection_confidence=0.5)
    detector = mp_vision.FaceDetector.create_from_options(options)

    cap = cv2.VideoCapture(video_path)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    
    best_face = None
    
    for pct in [0.1, 0.3, 0.5, 0.7, 0.9]:
        cap.set(cv2.CAP_PROP_POS_FRAMES, int(total_frames * pct))
        ret, frame = cap.read()
        if not ret: continue
        
        image_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=image_rgb)
        
        detection_result = detector.detect(mp_image)
        
        if len(detection_result.detections) > 0:
            detection = detection_result.detections[0]
            bbox = detection.bounding_box
            x = bbox.origin_x
            y = bbox.origin_y
            w = bbox.width
            h = bbox.height
            best_face = (x, y, w, h)
            break 
                
    cap.release()
    
    if best_face is not None:
        x, y, w, h = best_face
        cx, cy = x + w//2, y + h//2
        new_w = min(1920, int(w * 4.0)) # Ampliamos más para agarrar todo el torso
        new_h = min(1080, int(h * 4.0))
        new_x = max(0, cx - new_w//2)
        new_y = max(0, cy - new_h//2)
        
        if new_x + new_w > 1920: new_x = 1920 - new_w
        if new_y + new_h > 1080: new_y = 1080 - new_h
        
        print(f"Humano detectado por MediaPipe en X:{new_x}, Y:{new_y}.")
        return new_x, new_y, new_w, new_h
        
    print("No se detectó rostro humano con MediaPipe. Usando esquina inferior derecha.")
    return 1500, 600, 420, 480

def get_loudest_moment(audio_clip):
    print("Analizando picos de volumen en el audio (Momentos Hype)...")
    chunk_size = 2.0
    max_rms = 0
    best_time = 0
    duration = int(audio_clip.duration)
    
    for t in range(0, duration, int(chunk_size)):
        try:
            sub = audio_clip.subclipped(t, min(t + chunk_size, duration))
            arr = sub.to_soundarray(fps=11025) 
            rms = np.sqrt(np.mean(arr**2))
            if rms > max_rms:
                max_rms = rms
                best_time = t
        except Exception:
            pass
    return best_time, max_rms

def process_video(video_path):
    print(f"\n[{datetime.now()}] Procesando video V3 Ultra-Fast: {video_path}")
    basename = os.path.basename(video_path)
    game_name = basename.split('-')[0].strip() if '-' in basename else os.path.splitext(basename)[0].strip()
    
    face_x, face_y, face_w, face_h = get_dynamic_facecam_crop(video_path)
    
    # Extraer el momento más fuerte rápidamente
    audio_clip = AudioFileClip(video_path)
    best_time, max_rms = get_loudest_moment(audio_clip)
    audio_clip.close()
    
    start_time_vol = max(0, best_time - 35)
    end_time_vol = min(audio_clip.duration, best_time + 20)
    
    # Transcripción Whisper para TODOS los subtítulos
    print("Cargando Whisper (Transcribiendo con timestamps de palabras)...")
    model = whisper.load_model("base")
    result = model.transcribe(video_path, word_timestamps=True)
    
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # Preparar el FFMPEG Nativo (Reemplazando MoviePy)
    ass_filename = f"subs_{game_name}.ass".replace(" ", "")
    ass_path = os.path.join(OUTPUT_DIR, ass_filename)
    
    # Generar el archivo ASS con TODAS las palabras de ese lapso
    generate_ass(result["segments"], ass_path, start_time_vol, end_time_vol)
    
    date_str = datetime.now().strftime("%Y-%m-%d")
    final_out = f"{date_str}_TMP_{game_name.replace(' ', '')}_VOLUMEN.mp4"
    final_out_full = os.path.join(OUTPUT_DIR, final_out)
    
    hook_text = "¡MIRA ESTO!"
    
    # C++ FFMPEG Filter Complex (Velocidad Extrema)
    filter_complex = (
        f"[0:v]crop=1080:960:(iw-1080)/2:(ih-960)/2[top];"
        f"[0:v]crop={face_w}:{face_h}:{face_x}:{face_y},scale=1080:960[bottom];"
        f"[top][bottom]vstack=inputs=2[stacked];"
        f"[stacked]subtitles='{ass_filename}',"
        f"drawtext=text='{hook_text}':fontcolor=white:fontsize=120:x=(w-text_w)/2:y=900:enable='between(t,0,3)':box=1:boxcolor=magenta@0.8:boxborderw=20,"
        f"drawtext=text='@Leito4Gaming':fontcolor=white:fontsize=60:x=(w-text_w)/2:y=h-150:box=1:boxcolor=black@0.6:boxborderw=10[v]"
    )
    
    ffmpeg_cmd = [
        "ffmpeg", "-y", 
        "-ss", str(start_time_vol), 
        "-t", str(end_time_vol - start_time_vol), 
        "-i", video_path,
        "-filter_complex", filter_complex,
        "-map", "[v]",
        "-map", "0:a",
        "-c:v", "libx264", "-preset", "ultrafast",
        "-c:a", "aac",
        final_out
    ]
    
    print("Renderizando clip final con motor C++ FFmpeg...")
    subprocess.run(ffmpeg_cmd, check=True, cwd=OUTPUT_DIR)
    
    # Log exitoso
    output_data = {
        "status": "success",
        "game": game_name,
        "filepath": final_out_full,
    }
    print("===ANTIGRAVITY_DATA===")
    print(json.dumps(output_data))
    print("======================")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', type=str, required=True)
    args = parser.parse_args()
    
    if os.path.isdir(args.input):
        for f in os.listdir(args.input):
            if f.endswith(".mp4") or f.endswith(".mkv"):
                process_video(os.path.join(args.input, f))
    elif os.path.isfile(args.input):
        process_video(args.input)
