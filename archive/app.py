from flask import Flask, render_template, request, jsonify
import os
import json
import subprocess

app = Flask(__name__)

BASE_DIR = r"C:\Users\leone\Desktop\OBS Grabaciones\Exports\Complete Games"
ANALYSIS_FILE = os.path.join(BASE_DIR, "analysis.json")
VIDEO_DIR = r"D:\OBS Grabaciones Secondary Disk\OBS Videos\The Closing Shift\Test"
ASS_DIR = r"C:\Users\leone\Desktop\OBS Grabaciones\Exports\Clips_AI"
TEMP_CLIPS_DIR = os.path.join(BASE_DIR, "temp_clips")
FFMPEG_BIN = r"C:\Users\leone\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1.1-full_build\bin\ffmpeg.exe"

os.makedirs(TEMP_CLIPS_DIR, exist_ok=True)

def get_clips_data():
    if not os.path.exists(ANALYSIS_FILE):
        return [{"id": "clip_mock", "start": 0, "end": 10}], "video_mock.mkv"
    with open(ANALYSIS_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get("proposals", []), data.get("video", "")

@app.route("/")
def index():
    clips, video_name = get_clips_data()
    for clip in clips:
        ass_path = os.path.join(ASS_DIR, f"subs_{clip['id']}.ass")
        if not os.path.exists(ass_path):
            ass_path = os.path.join(ASS_DIR, "subs_clip_1.ass")
            
        clip['ass_text'] = ""
        if os.path.exists(ass_path):
            with open(ass_path, "r", encoding="utf-8") as f:
                clip['ass_text'] = f.read()
                
    return render_template("index.html", clips=clips, video_name=video_name)

@app.route("/api/export", methods=["POST"])
def export_clip():
    data = request.json
    clip_id = data.get("clip_id")
    start = data.get("start")
    end = data.get("end")
    ass_text = data.get("ass_text", "")
    video_name = data.get("video_name")
    
    fx = data.get("fx", 0)
    fy = data.get("fy", 0)
    fw = data.get("fw", 1920)
    fh = data.get("fh", 1080)
    
    gx = data.get("gx", 0)
    gy = data.get("gy", 0)
    gw = data.get("gw", 1920)
    gh = data.get("gh", 1080)
    
    ass_path = os.path.join(ASS_DIR, f"subs_{clip_id}.ass")
    with open(ass_path, "w", encoding="utf-8") as f:
        f.write(ass_text)
        
    video_path = os.path.join(VIDEO_DIR, video_name)
    out_file = os.path.join(TEMP_CLIPS_DIR, f"{clip_id}_render.mp4")
    
    # IMPORTANTE: Parche FFmpeg para rutas absolutas en Windows
    ass_ff = ass_path.replace("\\", "/").replace(":", "\\:")
    
    filter_complex = f"[0:v]crop={fw}:{fh}:{fx}:{fy},scale=1080:960[top];[0:v]crop={gw}:{gh}:{gx}:{gy},scale=1080:960[bottom];[top][bottom]vstack=inputs=2[v_base];[v_base]subtitles='{ass_ff}'[v]"
    
    cmd = [
        FFMPEG_BIN, "-y", "-ss", str(start), "-t", str(float(end) - float(start)), "-i", video_path,
        "-filter_complex", filter_complex,
        "-map", "[v]", "-map", "0:a",
        "-c:v", "libx264", "-preset", "ultrafast", "-crf", "23",
        "-c:a", "aac", out_file
    ]
    
    subprocess.Popen(cmd)
    
    return jsonify({"success": True, "output": out_file})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True, use_reloader=False)
