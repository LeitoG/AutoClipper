import os
import json
import subprocess
import cv2
import mediapipe as mp
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision as mp_vision
import urllib.request

FFMPEG_BIN = r"C:\Users\leone\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1.1-full_build\bin\ffmpeg.exe"
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
        "Style: Default, Impact, 80, &H00FFFFFF, &H00000000, &H00000000, -1, 0, 2, 700, 6, 3",
        "",
        "[Events]",
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text"
    ]
    
    for segment in segments:
        words = segment.get("words", [])
        for i, w in enumerate(words):
            w_start = w["start"] - start_offset
            w_end = w["end"] - start_offset
            
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

def get_dynamic_facecam_crop(video_path, start_sec):
    print(f"Buscando rostro con MediaPipe en el segundo {start_sec}...")
    model_path = os.path.join(OUTPUT_DIR, 'blaze_face_short_range.tflite')
    base_options = mp_python.BaseOptions(model_asset_path=model_path)
    options = mp_vision.FaceDetectorOptions(base_options=base_options, min_detection_confidence=0.5)
    detector = mp_vision.FaceDetector.create_from_options(options)

    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS)
    cap.set(cv2.CAP_PROP_POS_FRAMES, int(start_sec * fps))
    
    best_face = None
    for _ in range(30):
        ret, frame = cap.read()
        if not ret: break
        image_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=image_rgb)
        detection_result = detector.detect(mp_image)
        
        if len(detection_result.detections) > 0:
            detection = detection_result.detections[0]
            bbox = detection.bounding_box
            x, y, w, h = bbox.origin_x, bbox.origin_y, bbox.width, bbox.height
            best_face = (x, y, w, h)
            break
            
    cap.release()
    
    if best_face is not None:
        x, y, w, h = best_face
        cx, cy = x + w//2, y + h//2
        new_w = min(1920, int(w * 3.5))
        new_h = min(1080, int(h * 3.5))
        new_x = max(0, cx - new_w//2)
        new_y = max(0, cy - new_h//2)
        if new_x + new_w > 1920: new_x = 1920 - new_w
        if new_y + new_h > 1080: new_y = 1080 - new_h
        return new_x, new_y, new_w, new_h
        
    return 1500, 600, 420, 480

def render_clip(video_path, clip_data, segments):
    cid = clip_data["id"]
    start_t = clip_data["start"]
    end_t = clip_data["end"]
    template = clip_data["template"]
    
    print(f"Renderizando {cid} [{start_t}s - {end_t}s] con {template}...")
    
    face_x, face_y, face_w, face_h = get_dynamic_facecam_crop(video_path, start_t)
    
    ass_filename = f"subs_{cid}.ass"
    ass_path = os.path.join(OUTPUT_DIR, ass_filename)
    generate_ass(segments, ass_path, start_t, end_t)
    
    final_out = os.path.join(OUTPUT_DIR, f"{cid}_TheClosingShift.mp4")
    hook_text = "¡MIRA ESTO!"
    
    if template == "A":
        # Split 50/50
        filter_complex = (
            f"[0:v]crop={face_w}:{face_h}:{face_x}:{face_y},scale=1080:960[top];"
            f"[0:v]crop=1080:960:(iw-1080)/2:(ih-960)/2[bottom];"
            f"[top][bottom]vstack=inputs=2[stacked];"
            f"[stacked]subtitles='{ass_filename}',"
            f"drawtext=text='{hook_text}':fontcolor=white:fontsize=120:x=(w-text_w)/2:y=800:enable='between(t,0,3)':box=1:boxcolor=magenta@0.8:boxborderw=20,"
            f"drawtext=text='@Leito4Gaming':fontcolor=white:fontsize=60:x=(w-text_w)/2:y=h-150:box=1:boxcolor=black@0.6:boxborderw=10[v]"
        )
    else:
        # Inmersivo Overlay
        filter_complex = (
            f"[0:v]crop=ih*9/16:ih:(iw-ih*9/16)/2:0,scale=1080:1920[game];"
            f"[0:v]crop={face_w}:{face_h}:{face_x}:{face_y},scale=400:-1[face];"
            f"[game][face]overlay=x=(W-w)/2:y=150[stacked];"
            f"[stacked]subtitles='{ass_filename}',"
            f"drawtext=text='{hook_text}':fontcolor=white:fontsize=120:x=(w-text_w)/2:y=800:enable='between(t,0,3)':box=1:boxcolor=magenta@0.8:boxborderw=20,"
            f"drawtext=text='@Leito4Gaming':fontcolor=white:fontsize=60:x=(w-text_w)/2:y=h-150:box=1:boxcolor=black@0.6:boxborderw=10[v]"
        )

    ffmpeg_cmd = [
        FFMPEG_BIN, "-y", 
        "-ss", str(start_t), 
        "-t", str(end_t - start_t), 
        "-i", video_path,
        "-filter_complex", filter_complex,
        "-map", "[v]",
        "-map", "0:a",
        "-c:v", "libx264", "-preset", "ultrafast", "-crf", "23",
        "-c:a", "aac", "-b:a", "192k",
        final_out
    ]
    
    subprocess.run(ffmpeg_cmd, check=True, cwd=OUTPUT_DIR)
    print(f"Clip {cid} generado con éxito en: {final_out}")

if __name__ == "__main__":
    with open("full_transcription.json", "r", encoding="utf-8") as f:
        full_segments = json.load(f)
        
    clips = [
        {"id": "ElPedidoImposible", "start": 840, "end": 895, "template": "B"},
        {"id": "FotografiasYArma", "start": 1113, "end": 1164, "template": "A"},
        {"id": "InvasorEnCasa", "start": 1780, "end": 1825, "template": "A"}
    ]
    
    video_path = r"D:\OBS Grabaciones Secondary Disk\OBS Videos\The Closing Shift\Test\2026-06-14_21-09-06.mkv"
    
    for c in clips:
        render_clip(video_path, c, full_segments)
