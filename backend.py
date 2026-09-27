
from fastapi import FastAPI, HTTPException, Header, Request, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional, List
import os
import json
import subprocess
import traceback
import threading
import re
import base64
import datetime
import cv2
import io

export_progress = {}
analysis_progress = {"status": "idle", "percent": 0, "message": ""}

app = FastAPI(title="Auto Clipper V12 API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = r"C:\Users\leone\Desktop\OBS Grabaciones\Exports\Complete Games"
CONFIG_FILE = os.path.join(BASE_DIR, "config.json")
DB_DIR = os.path.join(BASE_DIR, "db")
os.makedirs(DB_DIR, exist_ok=True)

def get_analysis_file(video_name: str) -> str:
    if not video_name:
        return ""
    base = os.path.basename(video_name)
    safe_name = "".join([c for c in base if c.isalpha() or c.isdigit() or c in (' ', '.', '_', '-')]).rstrip()
    return os.path.join(DB_DIR, f"{safe_name}.json")

def find_video_path(video_identifier: str) -> str:
    if not video_identifier: return ""
    exact_path = os.path.join(VIDEO_DIR, video_identifier)
    if os.path.exists(exact_path): return exact_path
    base = os.path.basename(video_identifier)
    for root, dirs, files in os.walk(VIDEO_DIR):
        if base in files:
            return os.path.join(root, base)
    return exact_path

# Valores por defecto
VIDEO_DIR = r"D:\OBS Grabaciones Secondary Disk\OBS Videos\The Closing Shift\Test"
EXPORTS_DIR = os.path.join(BASE_DIR, "exports")

if os.path.exists(CONFIG_FILE):
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        cfg = json.load(f)
        VIDEO_DIR = cfg.get("video_dir", VIDEO_DIR)
        EXPORTS_DIR = cfg.get("exports_dir", EXPORTS_DIR)

if not os.path.exists(EXPORTS_DIR):
    os.makedirs(EXPORTS_DIR, exist_ok=True)

ASS_DIR = os.path.join(DB_DIR, "subs_data")
os.makedirs(ASS_DIR, exist_ok=True)

TEMP_CLIPS_DIR = os.path.join(BASE_DIR, "temp_clips")
HTML_FILE = os.path.join(BASE_DIR, "templates", "index.html")
FFMPEG_BIN = r"C:\Users\leone\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1.1-full_build\bin\ffmpeg.exe"

os.makedirs(TEMP_CLIPS_DIR, exist_ok=True)

class UpdateClipRequest(BaseModel):
    clip_id: str
    ass_text: str
    video_name: str
    words: list = []
    social_title: Optional[str] = None
    social_desc: Optional[str] = None
    start: Optional[float] = None
    end: Optional[float] = None
    export_name: Optional[str] = None
    subtitle_style: dict = {}

class SaveAllClipsRequest(BaseModel):
    video_name: str
    proposals: list

class ExportRequest(BaseModel):
    clip_id: str
    start: float
    end: float
    video_name: str
    fit_mode: str
    split_ratio: float = 0.5
    scenes: list
    words: list
    subtitle_style: dict = {}
    hook: Optional[dict] = None  # Expected: {"time": float, "textTop": str, "textBottom": str}
    outro: Optional[dict] = None
    stickers: list = []
    sounds: list = []
    export_track: Optional[str] = "mix"
    vol_voz: float = 1.0
    vol_juego: float = 1.0

class AudioPreviewRequest(BaseModel):
    video_name: str
    start: float
    end: float
    vol_voz: float = 1.0
    vol_juego: float = 1.0
    track_voz: int = 2
    track_juego: int = 3

class GenerateClipsRequest(BaseModel):
    prompt: str
    video_name: str
    search_modes: list[str] = ["volume"]
    max_clips: int = 15

class AddManualClipRequest(BaseModel):
    video_name: str
    start: float
    end: float

class MarkClipDoneRequest(BaseModel):
    clip_id: str
    video_name: str
    start: Optional[float] = None
    end: Optional[float] = None
    export_name: Optional[str] = None

class TranscribeRequest(BaseModel):
    clip_id: str
    video_name: str
    start: float
    end: float
    track: int = 2

class SetConfigRequest(BaseModel):
    video_dir: str
    exports_dir: str
    gemini_api_key: str = ""
    watermark: Optional[dict] = None

@app.get("/", response_class=HTMLResponse)
def serve_frontend():
    if os.path.exists(HTML_FILE):
        with open(HTML_FILE, "r", encoding="utf-8") as f:
            html = f.read()
            html = html.replace("__VIDEO_DIR__", VIDEO_DIR.replace("\\", "/"))
            html = html.replace("__EXPORTS_DIR__", EXPORTS_DIR.replace("\\", "/"))
            return HTMLResponse(content=html)
    return HTMLResponse(content="<h1>Index.html no encontrado</h1>", status_code=404)

@app.get("/progress")
def get_progress():
    return analysis_progress

@app.get("/config")
def get_config():
    gemini_key = ""
    watermark = None
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            cfg = json.load(f)
            gemini_key = cfg.get("gemini_api_key", "")
            watermark = cfg.get("watermark", None)
    return {"video_dir": VIDEO_DIR, "exports_dir": EXPORTS_DIR, "gemini_api_key": gemini_key, "watermark": watermark}

@app.post("/set_config")
def set_config(req: SetConfigRequest):
    global VIDEO_DIR, EXPORTS_DIR
    VIDEO_DIR = req.video_dir
    EXPORTS_DIR = req.exports_dir
    
    wm = req.watermark
    if wm and "dataUrl" in wm and wm["dataUrl"]:
        try:
            b64_data = wm["dataUrl"].split(",")[1]
            wm_path = os.path.join(DB_DIR, "watermark.png")
            with open(wm_path, "wb") as f:
                f.write(base64.b64decode(b64_data))
            wm["server_path"] = wm_path
            wm["dataUrl"] = ""
        except Exception as e:
            print("Error decoding watermark:", e)

    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump({"video_dir": VIDEO_DIR, "exports_dir": EXPORTS_DIR, "gemini_api_key": req.gemini_api_key, "watermark": wm}, f)
    
    if not os.path.exists(EXPORTS_DIR):
        os.makedirs(EXPORTS_DIR, exist_ok=True)
        
    return {"status": "success"}

@app.get("/browse_folder")
def browse_folder():
    import subprocess
    cmd = 'python -c "import tkinter as tk, tkinter.filedialog; root=tk.Tk(); root.attributes(\'-topmost\', True); root.withdraw(); print(tkinter.filedialog.askdirectory(parent=root, title=\'Seleccionar Carpeta\'))"'
    try:
        out = subprocess.check_output(cmd, shell=True).decode().strip()
        return {"path": out}
    except:
        return {"path": ""}

@app.get("/list_videos")
def list_videos():
    if not os.path.exists(VIDEO_DIR):
        return {"status": "error", "message": "Directorio de videos no existe"}
    videos = []
    for root, dirs, files in os.walk(VIDEO_DIR):
        dirs[:] = [d for d in dirs if d.lower() != "subidos"]
        for f in files:
            if f.lower().endswith(('.mp4', '.mkv')):
                full_path = os.path.join(root, f)
                rel_path = os.path.relpath(full_path, VIDEO_DIR).replace("\\", "/")
                videos.append(rel_path)
    
    rev_file = os.path.join(DB_DIR, "reviewed_videos.json")
    reviewed = {}
    if os.path.exists(rev_file):
        with open(rev_file, "r", encoding="utf-8") as f:
            reviewed = json.load(f)
            
    v_list = []
    for v in videos:
        is_rev = reviewed.get(v, False)
        an_file = get_analysis_file(v)
        is_analyzed = False
        if os.path.exists(an_file):
            try:
                with open(an_file, "r", encoding="utf-8") as af:
                    d = json.load(af)
                    if len(d.get("proposals", [])) > 0:
                        is_analyzed = True
            except:
                pass
        v_list.append({"name": v, "reviewed": is_rev, "analyzed": is_analyzed})
        
    return {"status": "success", "videos": v_list}

class MarkVideoReviewedRequest(BaseModel):
    video_name: str
    reviewed: bool

@app.post("/mark_video_reviewed")
def mark_video_reviewed(req: MarkVideoReviewedRequest):
    rev_file = os.path.join(DB_DIR, "reviewed_videos.json")
    if os.path.exists(rev_file):
        with open(rev_file, "r", encoding="utf-8") as f:
            data = json.load(f)
    else:
        data = {}
    
    data[req.video_name] = req.reviewed
    with open(rev_file, "w", encoding="utf-8") as f:
        json.dump(data, f)
    return {"status": "success"}

app.mount('/videos', StaticFiles(directory=VIDEO_DIR), name='videos')

@app.get("/ping")
def ping():
    return {"status": "ok"}

@app.get("/thumbnail")
def get_thumbnail(video: str, time: float, export: str = ""):
    # Intento 1: Video Exportado (si existe, para mostrar miniatura final)
    if export:
        export_path = os.path.join(EXPORTS_DIR, export)
        if not os.path.exists(export_path):
            # Buscar en subcarpetas (ej: "Subidos")
            for root, dirs, files in os.walk(EXPORTS_DIR):
                if export in files:
                    export_path = os.path.join(root, export)
                    break
                    
        if os.path.exists(export_path):
            try:
                cap = cv2.VideoCapture(export_path)
                cap.set(cv2.CAP_PROP_POS_MSEC, 0) # El exportado ya empieza en el clip
                ret, frame = cap.read()
                cap.release()
                
                if ret:
                    frame = cv2.resize(frame, (180, 320)) # Vertical
                    _, encoded_image = cv2.imencode('.jpg', frame)
                    return StreamingResponse(io.BytesIO(encoded_image.tobytes()), media_type="image/jpeg")
            except:
                pass

    # Intento 2: Video original
    vid_path = find_video_path(video)
    if os.path.exists(vid_path):
        try:
            cap = cv2.VideoCapture(vid_path)
            cap.set(cv2.CAP_PROP_POS_MSEC, time * 1000)
            ret, frame = cap.read()
            cap.release()
            
            if ret:
                frame = cv2.resize(frame, (320, 180))
                _, encoded_image = cv2.imencode('.jpg', frame)
                return StreamingResponse(io.BytesIO(encoded_image.tobytes()), media_type="image/jpeg")
        except:
            pass

    return StreamingResponse(io.BytesIO(b""), media_type="image/jpeg")

app.mount('/temp_clips', StaticFiles(directory=TEMP_CLIPS_DIR), name='temp_clips')
app.mount('/db', StaticFiles(directory=DB_DIR), name='db')

import shutil
import time

@app.post("/upload_asset")
def upload_asset(file: UploadFile = File(...)):
    try:
        ext = os.path.splitext(file.filename)[1].lower()
        unique_name = f"asset_{int(time.time()*1000)}{ext}"
        save_path = os.path.join(TEMP_CLIPS_DIR, unique_name)
        with open(save_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        if ext == '.mov':
            # Convertir MOV (ProRes) a WEBM con canal alfa para que el navegador lo pueda reproducir
            webm_path = save_path.replace('.mov', '.webm')
            try:
                import subprocess
                subprocess.run([FFMPEG_BIN, "-v", "error", "-y", "-i", save_path, "-c:v", "libvpx-vp9", "-pix_fmt", "yuva420p", webm_path], check=True)
                if os.path.exists(webm_path):
                    os.remove(save_path)
                    save_path = webm_path
                    unique_name = unique_name.replace('.mov', '.webm')
            except Exception as e:
                print("Error converting MOV to WEBM:", e)
        
        duration = 5.0
        try:
            import subprocess
            cmd = ['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'default=noprint_wrappers=1:nokey=1', save_path]
            out = subprocess.check_output(cmd, stderr=subprocess.DEVNULL).decode().strip()
            if out and out != 'N/A': duration = float(out)
        except Exception:
            pass
            
        return {"status": "success", "url": f"/temp_clips/{unique_name}", "path": save_path, "duration": duration}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.get("/export_progress/{clip_id}")
def get_export_progress(clip_id: str):
    return {"progress": export_progress.get(clip_id, "0")}

def run_ffmpeg(cmd, clip_id, total_duration):
    export_progress[clip_id] = "0"
    total_dur = total_duration
    try:
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL, universal_newlines=True)
        stdout_lines = []
        for line in process.stdout:
            stdout_lines.append(line)
            if "out_time_ms=" in line:
                ms_str = line.strip().split("=")[1]
                if ms_str.isdigit() and total_dur > 0:
                    ms = int(ms_str) / 1000000.0
                    percent = min(99, int((ms / total_dur) * 100))
                    export_progress[clip_id] = str(percent)
        process.wait()
        if process.returncode != 0:
            raise Exception("FFmpeg exit code " + str(process.returncode) + "\n" + "".join(stdout_lines[-50:]))
            
        # Generar e incrustar miniatura como portada para Windows Explorer
        out_file = cmd[-1]
        temp_jpg = out_file + ".jpg"
        temp_mp4 = out_file + ".tmp.mp4"
        
        try:
            # Extraer primer frame (el hook)
            subprocess.run([FFMPEG_BIN, "-y", "-i", out_file, "-vframes", "1", "-q:v", "2", temp_jpg], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
            # Incrustar frame como attached_pic
            if os.path.exists(temp_jpg):
                remux_cmd = [
                    FFMPEG_BIN, "-y",
                    "-i", out_file,
                    "-i", temp_jpg,
                    "-map", "0", "-map", "1",
                    "-c", "copy",
                    "-c:v:1", "mjpeg",
                    "-disposition:v:1", "attached_pic",
                    temp_mp4
                ]
                remux_proc = subprocess.run(remux_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                
                if remux_proc.returncode == 0 and os.path.exists(temp_mp4):
                    os.replace(temp_mp4, out_file)
                    
            if os.path.exists(temp_jpg):
                os.remove(temp_jpg)
            if os.path.exists(temp_mp4):
                os.remove(temp_mp4)
        except Exception as thumb_e:
            print(f"Error generando miniatura (ignorado): {thumb_e}")
            
        export_progress[clip_id] = "100"
    except Exception as e:
        export_progress[clip_id] = "-1"
        try:
            with open(os.path.join(BASE_DIR, "ffmpeg_error.log"), "w", encoding="utf-8", errors="replace") as f:
                f.write(f"Error en run_ffmpeg: {e}\n{traceback.format_exc()}")
        except Exception as write_err:
            print(f"Failed to write ffmpeg_error.log: {write_err}")

@app.get("/clips")
def get_clips(video_name: str = ""):
    try:
        analysis_file = get_analysis_file(video_name)
        if not analysis_file or not os.path.exists(analysis_file):
            return {"status": "success", "data": {"clips": [], "completed_clips": [], "video_name": video_name}}
            
        with open(analysis_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            
        proposals_raw = data.get("proposals", [])
        
        # Filtro de Calidad SemÃ¡ntico
        bad_words = ["notebook", "temperatura", "sobrecalentamiento", "pc"]
        proposals_filtered = []
        for clip in proposals_raw:
            reason = str(clip.get("reason", "")).lower()
            context = str(clip.get("context", "")).lower()
            text = str(clip.get("transcript", "")).lower()
            combined = reason + " " + context + " " + text
            
            if not any(bw in combined for bw in bad_words):
                proposals_filtered.append(clip)
        
        for clip in proposals_filtered:
            ass_path = os.path.join(ASS_DIR, f"subs_{clip['id']}.ass")
            if not os.path.exists(ass_path):
                ass_path = os.path.join(ASS_DIR, "subs_clip_1.ass")
            
            clip['ass_text'] = ""
            if os.path.exists(ass_path):
                with open(ass_path, "r", encoding="utf-8") as f:
                    clip['ass_text'] = f.read()
                    
        return {"status": "success", "data": {
            "clips": proposals_filtered, 
            "completed_clips": data.get("completed_proposals", []),
            "completed_ranges": data.get("completed_ranges", []),
            "rejected_clips": data.get("rejected_proposals", []),
            "video_name": video_name
        }}
        
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.post("/generate_clips")
def generate_clips(req: GenerateClipsRequest):
    try:
        import time
        import uuid
        import subprocess
        import re
        
        video_file_name = req.video_name
        if not video_file_name:
            return {"status": "error", "message": "No hay video activo."}
            
        analysis_file = get_analysis_file(video_file_name)
        data = {"video": video_file_name, "proposals": [], "completed_proposals": [], "completed_ranges": []}
        if analysis_file and os.path.exists(analysis_file):
            with open(analysis_file, "r", encoding="utf-8") as f:
                data = json.load(f)
        
        data["video"] = video_file_name
        if analysis_file:
            with open(analysis_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4)
            
        video_path = find_video_path(video_file_name)
        if not os.path.exists(video_path):
            return {"status": "error", "message": f"Video no encontrado: {video_path}"}
            
        gemini_api_key = ""
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                gemini_api_key = json.load(f).get("gemini_api_key", "")
                
        if not gemini_api_key:
            return {"status": "error", "message": "No se ha configurado la API Key de Gemini en los ajustes."}
            
        try:
            import pipeline
            import importlib
            importlib.reload(pipeline)
            from pipeline import analyze_video_local_first, analyze_video_semantic
        except ImportError:
            return {"status": "error", "message": "Falta el archivo pipeline.py."}
            
        def progress_cb(percent, msg):
            analysis_progress["percent"] = percent
            analysis_progress["message"] = msg
            
        analysis_progress["status"] = "processing"
        analysis_progress["percent"] = 5
        analysis_progress["message"] = "Iniciando anÃ¡lisis..."
            
        # Recopilar zonas a excluir (clips ya generados o completados)
        exclusion_zones = []
        for p in data.get("proposals", []):
            exclusion_zones.append((p.get("start", 0), p.get("end", 0)))
        for p in data.get("completed_proposals", []):
            exclusion_zones.append((p.get("start", 0), p.get("end", 0)))
        for p in data.get("completed_ranges", []):
            exclusion_zones.append((p.get("start", 0), p.get("end", 0)))
        for p in data.get("rejected_proposals", []):
            exclusion_zones.append((p.get("start", 0), p.get("end", 0)))
            
        max_id_val = 0
        all_existing = data.get("proposals", []) + data.get("completed_proposals", []) + data.get("rejected_proposals", [])
        for ex in all_existing:
            if str(ex.get("id", "")).startswith("clip_"):
                try:
                    num = int(ex["id"].split("_")[1])
                    if num > max_id_val: max_id_val = num
                except:
                    pass
        
        def incremental_save(c):
            nonlocal max_id_val
            s, e = c['start'], c['end']
            overlap = False
            for p in data.get("proposals", []) + data.get("completed_proposals", []) + data.get("completed_ranges", []) + data.get("rejected_proposals", []):
                if max(s, p['start']) < min(e, p['end']): overlap = True
            if overlap: return

            max_id_val += 1
            c["id"] = f"clip_{max_id_val}"
            ass_path = os.path.join(ASS_DIR, f"subs_{c['id']}.ass")
            if not os.path.exists(ass_path):
                try:
                    import shutil
                    shutil.copyfile(os.path.join(ASS_DIR, "subs_clip_1.ass"), ass_path)
                except:
                    with open(ass_path, "w", encoding="utf-8") as f: f.write("")
            with open(ass_path, "r", encoding="utf-8") as f: c["ass_text"] = f.read()

            c.update({
                "template": c.get("template", "face_game"),
                "cropState": c.get("cropState", {
                    "splitY": 960,
                    "face": {"x": 58, "y": 808, "w": 384, "h": 216},
                    "game": {"x": 0, "y": 0, "w": 1920, "h": 1080},
                    "full": {"x": 0, "y": 0, "w": 1920, "h": 1080},
                    "subs": {"x": 530, "y": 744, "w": 860, "h": 336}
                })
            })
            
            data.setdefault("proposals", []).append(c)
            data["proposals"].sort(key=lambda x: x["start"])
            if analysis_file:
                with open(analysis_file, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=4)
                    
        all_new_clips = []
        total_in = 0
        total_out = 0
        
        if "volume" in req.search_modes:
            print("Iniciando Pipeline de Ahorro de Tokens Local-First...")
            def prog_vol(pct, msg): progress_cb(int(pct/2), "MODO ACCIÃ“N: " + msg) if "semantic" in req.search_modes else progress_cb(pct, msg)
            nc, tin, tout = analyze_video_local_first(
                video_path, req.prompt, gemini_api_key, TEMP_CLIPS_DIR, prog_vol, exclusion_zones, incremental_save, req.max_clips
            )
            all_new_clips.extend(nc)
            total_in += tin
            total_out += tout
            # Actualizar exclusiones para que semantic no repita
            for p in nc: exclusion_zones.append((p.get("start", 0), p.get("end", 0)))
            
        if "semantic" in req.search_modes:
            print("Iniciando Pipeline SemÃ¡ntico (Whisper + Gemini Texto)")
            def prog_sem(pct, msg): progress_cb(50 + int(pct/2), "MODO HISTORIA: " + msg) if "volume" in req.search_modes else progress_cb(pct, msg)
            nc, tin, tout = analyze_video_semantic(
                video_path, req.prompt, gemini_api_key, TEMP_CLIPS_DIR, prog_sem, exclusion_zones, incremental_save, req.max_clips
            )
            all_new_clips.extend(nc)
            total_in += tin
            total_out += tout
        
        analysis_progress["status"] = "idle"
        
        # Guardar costos
        COSTS_FILE = os.path.join(DB_DIR, "cost_history.json")
        costs_data = {}
        if os.path.exists(COSTS_FILE):
            with open(COSTS_FILE, "r", encoding="utf-8") as f:
                costs_data = json.load(f)
                
        current_month = datetime.datetime.now().strftime("%Y-%m")
        if current_month not in costs_data:
            costs_data[current_month] = {"input_tokens": 0, "output_tokens": 0, "cost": 0.0}
            
        costs_data[current_month]["input_tokens"] += total_in
        costs_data[current_month]["output_tokens"] += total_out
        
        # Gemini 1.5 Flash pricing approx
        cost_in = (total_in / 1_000_000) * 0.075
        cost_out = (total_out / 1_000_000) * 0.30
        costs_data[current_month]["cost"] += (cost_in + cost_out)
        
        with open(COSTS_FILE, "w", encoding="utf-8") as f:
            json.dump(costs_data, f, indent=4)
        
        if not all_new_clips:
            return {"status": "error", "message": "No se encontraron clips viables o la IA rechazÃ³ los segmentos detectados."}
            
        return {"status": "success", "message": f"{len(all_new_clips)} Clips generados exitosamente"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.post("/add_manual_clip")
def add_manual_clip(req: AddManualClipRequest):
    try:
        import uuid
        analysis_file = get_analysis_file(req.video_name)
        
        data = {}
        if analysis_file and os.path.exists(analysis_file):
            with open(analysis_file, "r", encoding="utf-8") as f:
                data = json.load(f)
        
        if "proposals" not in data:
            data["proposals"] = []
            
        clip_id = f"manual_{uuid.uuid4().hex[:8]}"
        
        new_clip = {
            "id": clip_id,
            "start": req.start,
            "end": req.end,
            "reason": "Clip aÃ±adido manualmente",
            "virality_score": 100,
            "transcript": "",
            "social_title": "Clip Manual",
            "social_desc": "",
            "yt_title": "Clip Manual",
            "yt_desc": "",
            "yt_tags": "#Leito4Gaming, #Leito4GamingPlus",
            "template": "face_game",
            "cropState": {
                "splitY": 960,
                "face": {"x": 58, "y": 808, "w": 384, "h": 216},
                "game": {"x": 0, "y": 0, "w": 1920, "h": 1080},
                "full": {"x": 0, "y": 0, "w": 1920, "h": 1080},
                "subs": {"x": 530, "y": 744, "w": 860, "h": 336}
            }
        }
        
        data["proposals"].append(new_clip)
        
        if analysis_file:
            with open(analysis_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4)
                
        return {"status": "success", "message": "Clip manual aÃ±adido", "clip_id": clip_id}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.post("/mark_clip_done")
def mark_clip_done(req: MarkClipDoneRequest):
    try:
        import csv
        import datetime
        analysis_file = get_analysis_file(req.video_name)
        if not analysis_file or not os.path.exists(analysis_file):
            return {"status": "error", "message": "No analysis.json"}
            
        with open(analysis_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            
        completed_ranges = data.get("completed_ranges", [])
        proposals = data.get("proposals", [])
        
        target_clip = next((c for c in proposals if c["id"] == req.clip_id), None)
        if target_clip:
            if req.start is not None:
                target_clip["start"] = req.start
            if req.end is not None:
                target_clip["end"] = req.end
            if req.export_name is not None:
                target_clip["export_name"] = req.export_name
            
            completed_ranges.append({"start": target_clip["start"], "end": target_clip["end"]})
            data["completed_ranges"] = completed_ranges
            
            # Save full clip to completed_proposals
            completed_proposals = data.get("completed_proposals", [])
            completed_proposals.append(target_clip)
            data["completed_proposals"] = completed_proposals
            
            data["proposals"] = [c for c in proposals if c["id"] != req.clip_id]
            
            with open(analysis_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
                
            # APPEND TO CSV
            csv_file = os.path.join(DB_DIR, "historial_clips.csv")
            file_exists = os.path.isfile(csv_file)
            with open(csv_file, 'a', newline='', encoding='utf-8-sig') as f:
                writer = csv.writer(f)
                if not file_exists:
                    writer.writerow(['Fecha', 'Video Origen', 'Clip ID', 'Export Name', 'Titulo/Razon', 'Inicio', 'Fin', 'Duracion'])
                now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                dur = round(target_clip['end'] - target_clip['start'], 2)
                video_src = data.get("video", "Desconocido")
                export_name = target_clip.get('export_name', '')
                writer.writerow([now, video_src, req.clip_id, export_name, target_clip.get('reason', ''), target_clip['start'], target_clip['end'], dur])
                
        return {"status": "success"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

class RestoreClipRequest(BaseModel):
    clip_id: str
    video_name: str

@app.post("/restore_clip")
def restore_clip(req: RestoreClipRequest):
    try:
        analysis_file = get_analysis_file(req.video_name)
        if not analysis_file or not os.path.exists(analysis_file):
            return {"status": "error", "message": "No analysis.json"}
            
        with open(analysis_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            
        completed_proposals = data.get("completed_proposals", [])
        rejected_proposals = data.get("rejected_proposals", [])
        proposals = data.get("proposals", [])
        
        target = next((c for c in completed_proposals if c["id"] == req.clip_id), None)
        if not target:
            target = next((c for c in rejected_proposals if c["id"] == req.clip_id), None)
            
        if target:
            proposals.append(target)
            data["proposals"] = proposals
            data["completed_proposals"] = [c for c in completed_proposals if c["id"] != req.clip_id]
            data["rejected_proposals"] = [c for c in rejected_proposals if c["id"] != req.clip_id]
            
            # Quitar de completed_ranges si es posible
            completed_ranges = data.get("completed_ranges", [])
            data["completed_ranges"] = [cr for cr in completed_ranges if not (cr["start"] == target["start"] and cr["end"] == target["end"])]
            
            with open(analysis_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
                
        return {"status": "success"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.get("/get_costs")
def get_costs():
    try:
        COSTS_FILE = os.path.join(DB_DIR, "cost_history.json")
        if not os.path.exists(COSTS_FILE):
            return {"status": "success", "data": {}}
        with open(COSTS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return {"status": "success", "data": data}
    except Exception as e:
        return {"status": "error", "message": str(e)}

class UpdateClipReasonRequest(BaseModel):
    clip_id: str
    reason: str
    video_name: str

class DeleteClipRequest(BaseModel):
    clip_id: str
    video_name: str

@app.post("/delete_clip")
def delete_clip(req: DeleteClipRequest):
    try:
        analysis_file = get_analysis_file(req.video_name)
        if not analysis_file or not os.path.exists(analysis_file):
            return {"status": "error"}
            
        with open(analysis_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            
        proposals = data.get("proposals", [])
        
        target_clip = next((c for c in proposals if c["id"] == req.clip_id), None)
        if target_clip:
            rejected_proposals = data.get("rejected_proposals", [])
            rejected_proposals.append(target_clip)
            data["rejected_proposals"] = rejected_proposals
            
        data["proposals"] = [c for c in proposals if c["id"] != req.clip_id]
        
        with open(analysis_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
            
        return {"status": "success"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.post("/update_clip_reason")
def update_clip_reason(req: UpdateClipReasonRequest):
    try:
        analysis_file = get_analysis_file(req.video_name)
        if analysis_file and os.path.exists(analysis_file):
            with open(analysis_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            for c in data.get("proposals", []):
                if c["id"] == req.clip_id:
                    c["reason"] = req.reason
            with open(analysis_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
        return {"status": "success"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

class ClipFeedbackRequest(BaseModel):
    clip_id: str
    feedback: str
    video_name: str
    start: Optional[float] = None
    end: Optional[float] = None

@app.post("/clip_feedback")
def clip_feedback(req: ClipFeedbackRequest):
    try:
        import csv
        import random
        analysis_file = get_analysis_file(req.video_name)
        if analysis_file and os.path.exists(analysis_file):
            with open(analysis_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            target_clip = None
            for c in data.get("proposals", []):
                if c["id"] == req.clip_id:
                    c["feedback"] = req.feedback
                    target_clip = c
                    
            with open(analysis_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
                
            if target_clip:
                # Guardar en CSV original
                fb_file_csv = os.path.join(DB_DIR, "feedback_ia.csv")
                file_exists = os.path.isfile(fb_file_csv)
                with open(fb_file_csv, 'a', newline='', encoding='utf-8-sig') as f:
                    writer = csv.writer(f)
                    if not file_exists:
                        writer.writerow(['Clip ID', 'Razon original', 'Feedback'])
                    writer.writerow([req.clip_id, target_clip.get('reason', ''), req.feedback])
                
                # Guardar en JSON para InyecciÃ³n en IA
                fb_file_json = os.path.join(DB_DIR, "feedback_ia.json")
                feedback_data = []
                if os.path.exists(fb_file_json):
                    with open(fb_file_json, "r", encoding="utf-8") as f:
                        try:
                            feedback_data = json.load(f)
                        except json.JSONDecodeError:
                            feedback_data = []
                
                # Evitar duplicados del mismo clip ID
                feedback_data = [item for item in feedback_data if item.get('id') != req.clip_id]
                
                new_entry = {
                    "id": req.clip_id,
                    "feedback": req.feedback,
                    "reason": target_clip.get("reason", ""),
                    "transcript": target_clip.get("transcript", "")
                }
                feedback_data.append(new_entry)
                
                with open(fb_file_json, "w", encoding="utf-8") as f:
                    json.dump(feedback_data, f, indent=4, ensure_ascii=False)
                    
        return {"status": "success"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.post("/update_clip")
def update_clip(req: UpdateClipRequest):
    try:
        ass_path = os.path.join(ASS_DIR, f"subs_{req.clip_id}.ass")
        with open(ass_path, "w", encoding="utf-8") as f:
            f.write(req.ass_text)
            
        # Guardar las palabras exactas en analysis.json
        analysis_file = get_analysis_file(req.video_name)
        if analysis_file and os.path.exists(analysis_file):
            with open(analysis_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            proposals = data.get("proposals", [])
            for c in proposals:
                if c["id"] == req.clip_id:
                    c["words"] = req.words
                    if req.social_title is not None:
                        c["social_title"] = req.social_title
                    if req.social_desc is not None:
                        c["social_desc"] = req.social_desc
                    if req.start is not None:
                        c["start"] = req.start
                    if req.end is not None:
                        c["end"] = req.end
                    if req.export_name is not None:
                        c["export_name"] = req.export_name
            
            completed_proposals = data.get("completed_proposals", [])
            for c in completed_proposals:
                if c["id"] == req.clip_id:
                    c["words"] = req.words
                    if req.social_title is not None:
                        c["social_title"] = req.social_title
                    if req.social_desc is not None:
                        c["social_desc"] = req.social_desc
                    if req.start is not None:
                        c["start"] = req.start
                    if req.end is not None:
                        c["end"] = req.end
                    if req.export_name is not None:
                        c["export_name"] = req.export_name
            with open(analysis_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
                
        return {"status": "success", "message": "SubtÃ­tulos actualizados correctamente."}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.post("/save_all_clips")
def save_all_clips(req: SaveAllClipsRequest):
    try:
        analysis_file = get_analysis_file(req.video_name)
        if analysis_file and os.path.exists(analysis_file):
            with open(analysis_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            data["proposals"] = req.proposals
            with open(analysis_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
        return {"status": "success"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

class ExportRequest(BaseModel):
    clip_id: str
    start: float
    end: float
    video_name: str
    fit_mode: str
    scenes: List[dict]
    hook: Optional[dict] = None
    words: List[dict]
    subtitle_style: dict
    stickers: List[dict] = []
    outro: Optional[dict] = None
    export_name: Optional[str] = None
    social_title: Optional[str] = None
    social_desc: Optional[str] = None
    social_tags: Optional[str] = None
    export_track: Optional[str] = "mix"
    vol_voz: float = 1.0
    vol_juego: float = 1.0

@app.post("/export")
def export_clip(req: ExportRequest):
    try:
        video_path = find_video_path(req.video_name)
        if not os.path.exists(video_path):
            return {"status": "error", "message": f"Video fuente no encontrado: {video_path}"}
            
        if req.export_name:
            safe_name = "".join(c for c in req.export_name if c.isalnum() or c in " _-")
            if not safe_name: safe_name = req.clip_id + "_render"
            out_file = os.path.join(EXPORTS_DIR, f"{safe_name}.mp4")
        else:
            out_file = os.path.join(EXPORTS_DIR, f"{req.clip_id}_render.mp4")
        
        # 1. Generar SubtÃ­tulos DinÃ¡micos (.ass)
        ass_path = os.path.join(ASS_DIR, f"subs_{req.clip_id}_auto.ass")
        def format_time(ms):
            h = ms // 3600000
            m = (ms % 3600000) // 60000
            s = (ms % 60000) // 1000
            cs = (ms % 1000) // 10
            return f"{h}:{m:02d}:{s:02d}.{cs:02d}"


        with open(ass_path, "w", encoding="utf-8") as f:
            f.write("[Script Info]\nScriptType: v4.00+\nPlayResX: 1080\nPlayResY: 1920\n\n[V4+ Styles]\nFormat: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n")
            
            raw_color = req.subtitle_style.get("color", "&H00FF33CC&")
            s_color = raw_color[:-1] if raw_color.endswith("&") else raw_color
            s_font = req.subtitle_style.get("font", "Arial Black")
            s_anim = req.subtitle_style.get("anim", "bounce")
            s_size = req.subtitle_style.get("size", "95")
            
            use_bevel = req.subtitle_style.get("bevel", False)
            use_gradient = req.subtitle_style.get("gradient", False)
            
            def brighten_ass_color(c):
                if c.startswith("&H"): c = c[2:]
                if c.endswith("&"): c = c[:-1]
                if len(c) == 6:
                    b, g, r = int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16)
                elif len(c) == 8:
                    b, g, r = int(c[2:4], 16), int(c[4:6], 16), int(c[6:8], 16)
                else:
                    return "&HFFFFFF&"
                b = min(255, int(b * 1.6 + 50))
                g = min(255, int(g * 1.6 + 50))
                r = min(255, int(r * 1.6 + 50))
                return f"&H{b:02X}{g:02X}{r:02X}&"
            
            f.write(f"Style: Default,{s_font},{s_size},{s_color},&H000000FF,&H00000000,&H00000000,-1,0,0,0,100,100,0,0,1,12,0,5,10,10,10,1\n\n[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n")
            
            hook_offset = 0.017 if req.hook else 0.0
            for w in req.words:
                w_start = w.get("start", 0.0)
                w_end = w.get("end", 0.0)
                
                rel_offset = 0.0
                for sc in req.scenes:
                    i_start = max(w_start, sc['start'])
                    i_end = min(w_end, sc['end'])
                    
                    if i_start < i_end:
                        m_start = rel_offset + (i_start - sc['start'])
                        m_end = rel_offset + (i_end - sc['start'])
                        
                        s_ms = int((m_start + hook_offset) * 1000)
                        e_ms = int((m_end + hook_offset) * 1000)
                        
                        cc = sc['cropState']['subs']
                        sx, sy, sw, sh = cc['x'], cc['y'], cc['w'], cc['h']
                        draw_x = int((sx + sw/2) * (1080/1920))
                        draw_y = int((sy + sh/2) * (1920/1080))
                        
                        anim_tag = ""
                        if s_anim == "bounce":
                            anim_tag = r"{\fscx0\fscy0\t(0,100,\fscx120\fscy120)\t(100,200,\fscx100\fscy100)}"
                        elif s_anim == "pop":
                            anim_tag = r"{\fscx50\fscy50\t(0,150,\fscx100\fscy100)}"
                            
                        bevel_tag = ""
                        if use_bevel:
                            bevel_tag = r"\xbord5\ybord5\xshad4\yshad12\3c&H111111&\4c&H000000&"
                            
                        base_tag = f"{{\\pos({draw_x},{draw_y}){bevel_tag}}}"
                        f.write(f"Dialogue: 0,{format_time(s_ms)},{format_time(e_ms)},Default,,0,0,0,,{base_tag}{anim_tag}{w['text']}\n")
                        
                        if use_gradient:
                            bright_color = brighten_ass_color(s_color)
                            grad_tag = f"{{\\pos({draw_x},{draw_y})\\xbord0\\ybord0\\xshad0\\yshad0\\c{bright_color}\\clip(0,0,1080,{draw_y})}}"
                            f.write(f"Dialogue: 1,{format_time(s_ms)},{format_time(e_ms)},Default,,0,0,0,,{grad_tag}{anim_tag}{w['text']}\n")
                    rel_offset += (sc['end'] - sc['start'])

            # AÃ±adir stickers de texto al archivo ASS
            if req.stickers:
                for st in req.stickers:
                    if st.get("type") == "text":
                        st_start = st.get('start', 0.0)
                        st_end = st.get('end', 0.0)
                        
                        rel_offset = 0.0
                        for sc in req.scenes:
                            i_start = max(st_start, sc['start'])
                            i_end = min(st_end, sc['end'])
                            if i_start < i_end:
                                s_rel = rel_offset + (i_start - sc['start'])
                                e_rel = rel_offset + (i_end - sc['start'])
                                
                                s_ms = int(s_rel * 1000)
                                e_ms = int(e_rel * 1000)
                                
                                def html_to_ass_color(hc):
                                    hc = hc.replace('#', '')
                                    if len(hc) == 6:
                                        return f"&H00{hc[4:6]}{hc[2:4]}{hc[0:2]}&"
                                    return "&H00FFFFFF&"
                                
                                c_ass = html_to_ass_color(st.get('color', '#ffffff'))
                                sc_ass = html_to_ass_color(st.get('strokeColor', '#000000'))
                                s_font = st.get('font', 'Arial Black')
                                
                                x = int(st['x'])
                                y = int(st['y'])
                                w_st = int(st['w'])
                                h_st = int(st['h'])
                                
                                center_x = int(x + w_st/2)
                                center_y = int(y + h_st/2)
                                
                                anim_in = st.get('animIn', 'none')
                                anim_out = st.get('animOut', 'none')
                                
                                dur = e_ms - s_ms
                                
                                move_tag = ""
                                if anim_in == "swipe_left":
                                    move_tag = f"\\move({1080+w_st},{center_y},{center_x},{center_y},0,300)"
                                elif anim_in == "swipe_right":
                                    move_tag = f"\\move({-w_st},{center_y},{center_x},{center_y},0,300)"
                                elif anim_in == "swipe_up":
                                    move_tag = f"\\move({center_x},{1920+h_st},{center_x},{center_y},0,300)"
                                elif anim_in == "swipe_down":
                                    move_tag = f"\\move({center_x},{-h_st},{center_x},{center_y},0,300)"
                                    
                                if not move_tag and anim_out != "none":
                                    if anim_out == "swipe_left":
                                        move_tag = f"\\move({center_x},{center_y},{-w_st},{center_y},{dur-300},{dur})"
                                    elif anim_out == "swipe_right":
                                        move_tag = f"\\move({center_x},{center_y},{1080+w_st},{center_y},{dur-300},{dur})"
                                    elif anim_out == "swipe_up":
                                        move_tag = f"\\move({center_x},{center_y},{center_x},{-h_st},{dur-300},{dur})"
                                    elif anim_out == "swipe_down":
                                        move_tag = f"\\move({center_x},{center_y},{center_x},{1920+h_st},{dur-300},{dur})"
                                
                                if not move_tag:
                                    move_tag = f"\\pos({center_x},{center_y})"
                                    
                                margin_l = max(0, int(x))
                                margin_r = max(0, int(1080 - (x + w_st)))
                                    
                                tag = f"{{{move_tag}\\c{c_ass}\\3c{sc_ass}\\bord4\\fn{s_font}\\fs60\\an5\\q1}}"
                                f.write(f"Dialogue: 2,{format_time(s_ms)},{format_time(e_ms)},Default,,{margin_l},{margin_r},0,,{tag}{st.get('text', '')}\n")
                            rel_offset += (sc['end'] - sc['start'])

        ass_ff = ass_path.replace("\\", "/").replace(":", "\\:")
        
        # 2. Archivos e Inputs de FFmpeg
        inputs_args = ["-ss", str(req.start), "-i", video_path]
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
                if st.get("type") == "text":
                    continue
                
                if "server_path" in st and st["server_path"]:
                    st_path = st["server_path"]
                else:
                    b64_data = st.get("dataUrl", "").split(",")[1] if "dataUrl" in st else ""
                    if b64_data:
                        st_path = os.path.join(TEMP_CLIPS_DIR, f"st_{req.clip_id}_{i}.png")
                        with open(st_path, "wb") as f:
                            f.write(base64.b64decode(b64_data))
                    else:
                        continue
                
                is_video = st_path.lower().endswith(('.mov', '.mp4', '.webm'))
                
                # Para WebM con Alpha, forzamos el decodificador de VP9 o VP8
                if st_path.lower().endswith('.webm'):
                    try:
                        probe = subprocess.check_output(
                            [FFMPEG_BIN.replace("ffmpeg.exe", "ffprobe.exe"), "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=codec_name", "-of", "default=noprint_wrappers=1:nokey=1", st_path]
                        ).decode('utf-8').strip()
                        if probe == "vp8":
                            inputs_args.extend(["-stream_loop", "-1", "-vcodec", "libvpx", "-i", st_path])
                        else:
                            inputs_args.extend(["-stream_loop", "-1", "-vcodec", "libvpx-vp9", "-i", st_path])
                    except:
                        inputs_args.extend(["-stream_loop", "-1", "-vcodec", "libvpx-vp9", "-i", st_path])
                else:
                    if is_video:
                        inputs_args.extend(["-stream_loop", "-1", "-i", st_path])
                    else:
                        inputs_args.extend(["-i", st_path])
                    
                sticker_inputs.append({
                    "idx": input_idx, 
                    "x": st["x"], "y": st["y"], "w": st["w"], "h": st["h"],
                    "start": st.get("start", 0), "end": st.get("end", 9999),
                    "is_video": is_video,
                    "opacity": st.get("opacity", 1.0)
                })
                input_idx += 1
        
        # Watermark del sistema
        wm_idx = -1
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                cfg = json.load(f)
                wm = cfg.get("watermark")
                if wm and wm.get("server_path") and os.path.exists(wm["server_path"]):
                    inputs_args.extend(["-i", wm["server_path"]])
                    wm_idx = input_idx
                    input_idx += 1
                    
        # Sonidos adicionales
        sound_inputs = []
        for snd in getattr(req, "sounds", []):
            snd_path = snd.get("server_path", "")
            if os.path.exists(snd_path):
                inputs_args.extend(["-i", snd_path])
                sound_inputs.append({
                    "idx": input_idx,
                    "start": snd.get("start", 0),
                    "end": snd.get("end", 9999)
                })
                input_idx += 1
        
        try:
            probe_cmd = [FFMPEG_BIN.replace("ffmpeg.exe", "ffprobe.exe"), "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height", "-of", "csv=s=x:p=0", video_path]
            probe_out = subprocess.check_output(probe_cmd).decode('utf-8').strip()
            video_w, video_h = map(int, probe_out.split('x'))
        except Exception:
            video_w, video_h = 1920, 1080
            
        try:
            probe_a_cmd = [FFMPEG_BIN.replace("ffmpeg.exe", "ffprobe.exe"), "-v", "error", "-select_streams", "a", "-show_entries", "stream=index", "-of", "csv=p=0", video_path]
            probe_a_out = subprocess.check_output(probe_a_cmd).decode('utf-8').strip()
            num_audio_streams = len([x for x in probe_a_out.split('\n') if x.strip()])
        except Exception:
            num_audio_streams = 1
            
        def format_scene(s_input, scene, out_name):
            def safe_crop(c):
                raw_x = c.get('x', 0)
                raw_y = c.get('y', 0)
                raw_w = c.get('w', 1920)
                raw_h = c.get('h', 1080)
                
                # El UI siempre asume un contenedor 1920x1080
                container_w, container_h = 1920.0, 1080.0
                scale = min(container_w / video_w, container_h / video_h)
                
                # Resolucion con la que el video se dibuja dentro del contenedor
                draw_w = video_w * scale
                draw_h = video_h * scale
                
                # Offset debido al letterboxing
                offset_x = (container_w - draw_w) / 2
                offset_y = (container_h - draw_h) / 2
                
                # Revertir el mapeo
                x = max(0, int((raw_x - offset_x) / scale))
                y = max(0, int((raw_y - offset_y) / scale))
                w = max(2, int(raw_w / scale))
                h = max(2, int(raw_h / scale))
                
                # Hacer pares para FFmpeg (yuv420p)
                x -= x % 2
                y -= y % 2
                w -= w % 2
                h -= h % 2
                
                if x >= video_w: x = video_w - 2
                if y >= video_h: y = video_h - 2
                if x + w > video_w: w = video_w - x
                if y + h > video_h: h = video_h - y
                
                w -= w % 2
                h -= h % 2
                if w < 2: w = 2
                if h < 2: h = 2
                
                return w, h, x, y

            split_y = scene.get('cropState', {}).get('splitY', 960)
            
            if scene['template'] == 'face_game':
                f_w, f_h, f_x, f_y = safe_crop(scene['cropState']['face'])
                g_w, g_h, g_x, g_y = safe_crop(scene['cropState']['game'])
                
                face_h = int(split_y)
                face_h -= face_h % 2
                game_h = 1920 - face_h
                
                if req.fit_mode == "pad":
                    scale_f = min(1080 / f_w, face_h / f_h)
                    new_f_w = int(f_w * scale_f)
                    new_f_h = int(f_h * scale_f)
                    
                    scale_g = min(1080 / g_w, game_h / g_h)
                    new_g_w = int(g_w * scale_g)
                    new_g_h = int(g_h * scale_g)
                    
                    new_f_w -= new_f_w % 2
                    new_f_h -= new_f_h % 2
                    new_g_w -= new_g_w % 2
                    new_g_h -= new_g_h % 2
                    
                    f_pad_y = (face_h - new_f_h) // 2
                    g_pad_y = (game_h - new_g_h) // 2
                    
                    filter_parts.append(f"[{s_input}]split=2[f_{out_name}_s][g_{out_name}_s]")
                    filter_parts.append(f"[f_{out_name}_s]crop={f_w}:{f_h}:{f_x}:{f_y},scale={new_f_w}:{new_f_h},pad=1080:{face_h}:(1080-{new_f_w})/2:{f_pad_y}:black[face_{out_name}]")
                    filter_parts.append(f"[g_{out_name}_s]crop={g_w}:{g_h}:{g_x}:{g_y},scale={new_g_w}:{new_g_h},pad=1080:{game_h}:(1080-{new_g_w})/2:{g_pad_y}:black[game_{out_name}]")
                    
                    filter_parts.append(f"[face_{out_name}][game_{out_name}]vstack=inputs=2,setsar=1[{out_name}]")
                elif req.fit_mode == 'cover':
                    filter_parts.append(f"[{s_input}]split=2[vf_{out_name}][vg_{out_name}]")
                    filter_parts.append(f"[vf_{out_name}]crop={f_w}:{f_h}:{f_x}:{f_y},scale=1080:{face_h}:force_original_aspect_ratio=increase,crop=1080:{face_h}[face_{out_name}]")
                    filter_parts.append(f"[vg_{out_name}]crop={g_w}:{g_h}:{g_x}:{g_y},scale=1080:{game_h}:force_original_aspect_ratio=increase,crop=1080:{game_h}[game_{out_name}]")
                    
                    filter_parts.append(f"[face_{out_name}][game_{out_name}]vstack=inputs=2,setsar=1[{out_name}]")
                else:
                    filter_parts.append(f"[{s_input}]split=2[vf_{out_name}][vg_{out_name}]")
                    filter_parts.append(f"[vf_{out_name}]crop={f_w}:{f_h}:{f_x}:{f_y}[f_raw_{out_name}]")
                    filter_parts.append(f"[f_raw_{out_name}]split=2[f_bg_{out_name}][f_fg_{out_name}]")
                    filter_parts.append(f"[f_bg_{out_name}]scale=540:-1,boxblur=10:1,scale=1080:{face_h}:flags=bilinear,colorchannelmixer=rr=0.3:gg=0.3:bb=0.3[f_blur_{out_name}]")
                    filter_parts.append(f"[f_fg_{out_name}]scale=1080:{face_h}:force_original_aspect_ratio=decrease[f_scale_{out_name}]")
                    filter_parts.append(f"[f_blur_{out_name}][f_scale_{out_name}]overlay=(W-w)/2:(H-h)/2[face_{out_name}]")
                    
                    filter_parts.append(f"[vg_{out_name}]crop={g_w}:{g_h}:{g_x}:{g_y}[g_raw_{out_name}]")
                    filter_parts.append(f"[g_raw_{out_name}]split=2[g_bg_{out_name}][g_fg_{out_name}]")
                    filter_parts.append(f"[g_bg_{out_name}]scale=540:-1,boxblur=10:1,scale=1080:{game_h}:flags=bilinear,colorchannelmixer=rr=0.3:gg=0.3:bb=0.3[g_blur_{out_name}]")
                    filter_parts.append(f"[g_fg_{out_name}]scale=1080:{game_h}:force_original_aspect_ratio=decrease[g_scale_{out_name}]")
                    filter_parts.append(f"[g_blur_{out_name}][g_scale_{out_name}]overlay=(W-w)/2:(H-h)/2[game_{out_name}]")
                    filter_parts.append(f"[face_{out_name}][game_{out_name}]vstack=inputs=2,setsar=1[{out_name}]")
            else:
                c_w, c_h, c_x, c_y = safe_crop(scene['cropState']['full'])
                if req.fit_mode == 'pad':
                    scale_f = min(1080 / c_w, 1920 / c_h)
                    new_f_w = int(c_w * scale_f)
                    new_f_h = int(c_h * scale_f)
                    new_f_w -= new_f_w % 2
                    new_f_h -= new_f_h % 2
                    f_pad_x = (1080 - new_f_w) // 2
                    f_pad_y = (1920 - new_f_h) // 2
                    filter_parts.append(f"[{s_input}]crop={c_w}:{c_h}:{c_x}:{c_y},scale={new_f_w}:{new_f_h},pad=1080:1920:{f_pad_x}:{f_pad_y}:black,setsar=1[{out_name}]")
                elif req.fit_mode == 'cover':
                    filter_parts.append(f"[{s_input}]crop={c_w}:{c_h}:{c_x}:{c_y},scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,setsar=1[{out_name}]")
                else:
                    filter_parts.append(f"[{s_input}]crop={c_w}:{c_h}:{c_x}:{c_y}[full_raw_{out_name}]")
                    filter_parts.append(f"[full_raw_{out_name}]split=2[f_bg_{out_name}][f_fg_{out_name}]")
                    filter_parts.append(f"[f_bg_{out_name}]scale=540:960,boxblur=10:1,scale=1080:1920:flags=bilinear,colorchannelmixer=rr=0.3:gg=0.3:bb=0.3[f_blur_{out_name}]")
                    filter_parts.append(f"[f_fg_{out_name}]scale=1080:1920:force_original_aspect_ratio=decrease[f_scale_{out_name}]")
                    filter_parts.append(f"[f_blur_{out_name}][f_scale_{out_name}]overlay=(W-w)/2:(H-h)/2,setsar=1[{out_name}]")

        # Generar Hook (Si existe)
        inputs_concat = []
        if req.hook:
            h_time = max(0.0, req.hook.get('time', req.start) - req.start)
            h_text_top = req.hook.get('textTop', '').replace("'", "\\'").replace(":", "\\:")
            h_text_bottom = req.hook.get('textBottom', '').replace("'", "\\'").replace(":", "\\:")
            
            filter_parts.append(f"[0:v]trim=start={h_time:.6f}:end={h_time+0.1:.6f},trim=start_frame=0:end_frame=1,setpts=PTS-STARTPTS[hook_src]")
            # Formatear usando la configuraciÃ³n capturada (o fallback a la primera escena)
            hook_crop = req.hook.get("cropState")
            if not hook_crop:
                hook_crop = req.scenes[0]["cropState"]
                
            hook_scene = {
                "template": req.scenes[0]["template"],
                "cropState": hook_crop
            }
            format_scene("hook_src", hook_scene, "hook_fmt")
            # Dibujar caja y texto
            # Arial Black en Windows: C:/Windows/Fonts/ariblk.ttf
            font_path = "C\\:/Windows/Fonts/ariblk.ttf"
            
            # Start the draw pipeline with the formatted scene and add a black tint box
            draw_pipeline = f"[hook_fmt]drawbox=y=(ih-200)/2:color=black@0.0:width=iw:height=200:t=fill" # Empty transparent box just to chain if no text
            
            top_y_pct = req.hook.get('topY', 7.0)
            bottom_y_pct = req.hook.get('bottomY', 85.0)
            
            top_y_px = int((top_y_pct / 100.0) * 1920)
            bottom_y_px = int((bottom_y_pct / 100.0) * 1920)
            
            font_choice = req.hook.get('font', 'Arial Black')
            color_choice = req.hook.get('color', 'white')
            
            font_path = "C\\:/Windows/Fonts/ariblk.ttf"
            if font_choice == "Freude":
                local_ttf = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Freude.ttf").replace("\\", "/")
                local_otf = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Freude.otf").replace("\\", "/")
                if os.path.exists(local_ttf):
                    font_path = local_ttf.replace("C:", "C\\:")
                elif os.path.exists(local_otf):
                    font_path = local_otf.replace("C:", "C\\:")
                elif os.path.exists("C:/Windows/Fonts/Freude.ttf"):
                    font_path = "C\\:/Windows/Fonts/Freude.ttf"
                elif os.path.exists("C:/Windows/Fonts/Freude.otf"):
                    font_path = "C\\:/Windows/Fonts/Freude.otf"
                elif os.path.exists(os.path.expandvars("%LOCALAPPDATA%/Microsoft/Windows/Fonts/Freude.ttf")):
                    font_path = os.path.expandvars("%LOCALAPPDATA%/Microsoft/Windows/Fonts/Freude.ttf").replace("\\", "/").replace("C:", "C\\:")
                elif os.path.exists(os.path.expandvars("%LOCALAPPDATA%/Microsoft/Windows/Fonts/Freude.otf")):
                    font_path = os.path.expandvars("%LOCALAPPDATA%/Microsoft/Windows/Fonts/Freude.otf").replace("\\", "/").replace("C:", "C\\:")
                else:
                    font_path = "C\\:/Windows/Fonts/ariblk.ttf" # Safe fallback
            elif font_choice == "Impact":
                font_path = "C\\:/Windows/Fonts/impact.ttf"
            elif font_choice == "Montserrat":
                if os.path.exists("C:/Windows/Fonts/Montserrat-Bold.ttf"):
                    font_path = "C\\:/Windows/Fonts/Montserrat-Bold.ttf"
                else:
                    font_path = "C\\:/Windows/Fonts/ariblk.ttf"
                
            if h_text_top:
                draw_pipeline += f",drawbox=y={top_y_px - 35}:color=black@0.7:width=iw:height=150:t=fill,drawtext=fontfile='{font_path}':text='{h_text_top}':fontcolor={color_choice}:fontsize=80:x=(w-text_w)/2:y={top_y_px}:shadowcolor=black:shadowx=3:shadowy=3"
            
            if h_text_bottom:
                draw_pipeline += f",drawbox=y={bottom_y_px - 35}:color=black@0.7:width=iw:height=150:t=fill,drawtext=fontfile='{font_path}':text='{h_text_bottom}':fontcolor={color_choice}:fontsize=80:x=(w-text_w)/2:y={bottom_y_px}:shadowcolor=black:shadowx=3:shadowy=3"
                
            filter_parts.append(f"{draw_pipeline},setsar=1[out_hook]")
            inputs_concat.append("[out_hook]")

        # Generar Escenas Normales
        inputs_concat_a = []
        
        if req.hook:
            filter_parts.append(f"anullsrc=r=48000:cl=stereo:d=0.017[hook_a]")
            inputs_concat_a.append("[hook_a]")
            
        for i, scene in enumerate(req.scenes):
            s_start = max(0.0, scene['start'] - req.start)
            s_end = max(s_start + 0.001, scene['end'] - req.start)
            filter_parts.append(f"[0:v]trim=start={s_start:.6f}:end={s_end:.6f},setpts=PTS-STARTPTS[v_s{i}]")
            
            export_track = getattr(req, "export_track", "mix")
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
                filter_parts.append(f"[0:a:{a_idx}]atrim=start={s_start:.6f}:end={s_end:.6f},asetpts=PTS-STARTPTS[a_s{i}]")
            format_scene(f"v_s{i}", scene, f"out_{i}")
            inputs_concat.append(f"[out_{i}]")
            inputs_concat_a.append(f"[a_s{i}]")
        
        concat_str = ""
        for i in range(len(inputs_concat)):
            concat_str += f"{inputs_concat[i]}{inputs_concat_a[i]}"
        num_concat = len(inputs_concat)
        concat_str += f"concat=n={num_concat}:v=1:a=1[v_concat][a_concat_base]"
        filter_parts.append(concat_str)
        
        # Procesar Sonidos
        current_a = "a_concat_base"
        sound_amix_inputs = [f"[{current_a}]"]
        for i, snd in enumerate(sound_inputs):
            snd_start = snd['start']
            
            # Encontrar el inicio relativo en la timeline concatenada
            rel_offset = 0.0
            first_s_rel = None
            
            for sc in req.scenes:
                if sc['start'] <= snd_start <= sc['end']:
                    first_s_rel = rel_offset + (snd_start - sc['start'])
                    break
                rel_offset += (sc['end'] - sc['start'])
                
            if first_s_rel is not None:
                delay_ms = int(first_s_rel * 1000)
                filter_parts.append(f"[{snd['idx']}:a]adelay={delay_ms}|{delay_ms}[a_snd_{i}]")
                sound_amix_inputs.append(f"[a_snd_{i}]")
        
        if len(sound_amix_inputs) > 1:
            amix_inputs_str = "".join(sound_amix_inputs)
            # weights: 1 para el principal, y 1 para cada sonido
            weights = " ".join(["1"] * len(sound_amix_inputs))
            filter_parts.append(f"{amix_inputs_str}amix=inputs={len(sound_amix_inputs)}:duration=first:dropout_transition=0:weights='{weights}'[a_concat]")
        else:
            filter_parts.append(f"[{current_a}]anull[a_concat]")
        
        # Aplicar SubtÃ­tulos al video concatenado
        filter_parts.append(f"[v_concat]subtitles='{ass_ff}'[v_subs]")
        
        current_v = "v_subs"
        
        # Aplicar Stickers
        for i, st in enumerate(sticker_inputs):
            scale_w = int(st['w'])
            scale_h = int(st['h'])
            pos_x = int(st['x'])
            pos_y = int(st['y'])
            
            # Map start and end using intersection for duplicated scenes
            st_start = st['start']
            st_end = st['end']
            
            enable_exprs = []
            rel_offset = 0.0
            first_s_rel = None
            
            for sc in req.scenes:
                i_start = max(st_start, sc['start'])
                i_end = min(st_end, sc['end'])
                if i_start < i_end:
                    s_rel = rel_offset + (i_start - sc['start'])
                    e_rel = rel_offset + (i_end - sc['start'])
                    enable_exprs.append(f"between(t,{s_rel},{e_rel})")
                    if first_s_rel is None: first_s_rel = s_rel
                rel_offset += (sc['end'] - sc['start'])
                
            if not enable_exprs:
                continue
                
            enable_expr = "enable='" + "+".join(enable_exprs) + "'"
            
            filter_parts.append(f"[{st['idx']}:v]format=rgba,scale={scale_w}:{scale_h}[st_scaled_{i}]")
            
            if st['is_video']:
                # For videos, delay the presentation time so it starts playing exactly at first_s_rel.
                filter_parts.append(f"[st_scaled_{i}]setpts=PTS-STARTPTS+{first_s_rel}/TB[st_pts_{i}]")
                filter_parts.append(f"[{current_v}][st_pts_{i}]overlay={pos_x}:{pos_y}:{enable_expr}:eof_action=pass[v_st_{i}]")
            else:
                opacity_val = float(st.get('opacity', 1.0))
                if opacity_val < 1.0:
                    filter_parts.append(f"[st_scaled_{i}]colorchannelmixer=aa={opacity_val}[st_op_{i}]")
                    filter_parts.append(f"[{current_v}][st_op_{i}]overlay={pos_x}:{pos_y}:{enable_expr}[v_st_{i}]")
                else:
                    filter_parts.append(f"[{current_v}][st_scaled_{i}]overlay={pos_x}:{pos_y}:{enable_expr}[v_st_{i}]")
                
            current_v = f"v_st_{i}"
            
        # Aplicar Outro (Imagen final de 5s)
        if outro_idx != -1:
            filter_parts.append(f"[{outro_idx}:v]scale=1080:1920:force_original_aspect_ratio=decrease[out_fg]")
            filter_parts.append(f"[{outro_idx}:v]scale=540:960,boxblur=10:2,scale=1080:1920:flags=bilinear,colorchannelmixer=rr=0.3:gg=0.3:bb=0.3[out_bg]")
            filter_parts.append(f"[out_bg][out_fg]overlay=(W-w)/2:(H-h)/2[outro_fmt]")
            # Loop por 5 segundos (30fps = 150 frames aprox)
            filter_parts.append(f"[outro_fmt]loop=loop=150:size=1:start=0,setpts=N/FRAME_RATE/TB[outro_vid]")
            # Concatenar video principal con outro
            filter_parts.append(f"[{current_v}][outro_vid]concat=n=2:v=1:a=0[v_final]")
            current_v = "v_final"
            
        filter_parts.append(f"[{current_v}]copy[v_out]")
        filter_complex = ";".join(filter_parts)
        
        total_dur = sum(sc['end'] - sc['start'] for sc in req.scenes)
        if req.hook: total_dur += 1.5

            
        if outro_idx != -1: total_dur += 5.0
        
        cmd = [FFMPEG_BIN, "-y", "-threads", "0"] + inputs_args + [
            "-filter_complex", filter_complex,
            "-map", "[v_out]", "-map", "[a_concat]",
            "-c:v", "h264_nvenc", "-preset", "p2", "-cq", "25",
            "-c:a", "aac",
            "-progress", "pipe:1",
            out_file
        ]
        
        with open(os.path.join(BASE_DIR, "debug_cmd.txt"), "w", encoding="utf-8") as f:
            f.write(repr(cmd))
            
        threading.Thread(target=run_ffmpeg, args=(cmd, req.clip_id, total_dur)).start()
        
        # Generar archivo _redes.txt en DB_DIR
        if getattr(req, "clip_id", None):
            txt_path = os.path.join(DB_DIR, f"{req.clip_id}_redes.txt")
        else:
            txt_path = os.path.join(DB_DIR, f"{safe_name}_redes.txt" if req.export_name else "redes.txt")
            
        with open(txt_path, "w", encoding="utf-8") as f:
            if req.social_title:
                f.write("TITULO:\n" + req.social_title + "\n\n")
            if req.social_desc:
                f.write("DESCRIPCION:\n" + req.social_desc + "\n\n")
            if getattr(req, "social_tags", None):
                f.write("ETIQUETAS:\n" + req.social_tags + "\n")
                    
        return {"status": "success", "output": out_file, "message": "Render iniciado en segundo plano."}
    except Exception as e:
        return {"status": "error", "message": str(e), "trace": traceback.format_exc()}

@app.post("/transcribe")
def transcribe_audio(req: TranscribeRequest):
    try:
        video_path = find_video_path(req.video_name)
        if not os.path.exists(video_path):
            return {"status": "error", "message": "Video no encontrado."}
            
        temp_audio = os.path.join(TEMP_CLIPS_DIR, f"{req.clip_id}_audio.wav")
        cmd = [
            FFMPEG_BIN, "-y", "-ss", str(req.start), "-t", str(req.end - req.start),
            "-i", video_path, "-map", f"0:a:{req.track - 1}", "-vn", "-acodec", "pcm_s16le", "-ar", "16000", "-ac", "1", temp_audio
        ]
        import subprocess
        try:
            subprocess.run(cmd, check=True, capture_output=True)
        except subprocess.CalledProcessError as e:
            if req.track > 1:
                print(f"Advertencia: No se encontrÃ³ la Pista {req.track}. Cayendo de vuelta a la Pista 1 (0:a:0).")
                cmd[cmd.index("-map") + 1] = "0:a:0"
                subprocess.run(cmd, check=True, capture_output=True)
            else:
                raise Exception(f"FFmpeg error: {e.stderr.decode('utf-8', errors='ignore')}")
        
        import whisper
        print("Cargando modelo Whisper...")
        try:
            whisper_model = whisper.load_model("small")
        except:
            whisper_model = None
        result = whisper_model.transcribe(temp_audio, word_timestamps=True, language="es", 
            initial_prompt="boludo, wtf, la puta madre, ciervo, hotel, veneno.", 
            condition_on_previous_text=False, no_speech_threshold=0.6, logprob_threshold=-1.0)
        
        words_out = []
        for seg in result.get("segments", []):
            for w in seg.get("words", []):
                words_out.append({
                    "word": w["word"].strip(),
                    "start": req.start + w["start"],
                    "end": req.start + w["end"]
                })
                
        return {"status": "success", "words": words_out}
    except Exception as e:
        return {"status": "error", "message": str(e), "trace": traceback.format_exc()}

class ResetVideoRequest(BaseModel):
    video_name: str

@app.post("/reset_video")
def reset_video(req: ResetVideoRequest):
    try:
        analysis_file = get_analysis_file(req.video_name)
        if analysis_file and os.path.exists(analysis_file):
            data = {"video": req.video_name, "proposals": [], "completed_ranges": [], "completed_proposals": [], "rejected_proposals": []}
            with open(analysis_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4)
        return {"status": "success", "message": "Video reseteado."}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.get("/get_history")
def get_history():
    try:
        history = []
        if os.path.exists(DB_DIR):
            for file in os.listdir(DB_DIR):
                if file.endswith(".json") and file != "cost_history.json":
                    filepath = os.path.join(DB_DIR, file)
                    try:
                        with open(filepath, "r", encoding="utf-8") as f:
                            data = json.load(f)
                        video_name = data.get("video", file.replace(".json", ""))
                        completed = data.get("completed_proposals", [])
                        for c in completed:
                            c["video_name"] = video_name
                            c["db_file"] = file
                            history.append(c)
                    except:
                        pass
        return {"status": "success", "history": history}
    except Exception as e:
        return {"status": "error", "message": str(e)}

class MarkPublishedRequest(BaseModel):
    clip_id: str
    video_name: str

@app.post("/mark_published")
def mark_published(req: MarkPublishedRequest):
    try:
        analysis_file = get_analysis_file(req.video_name)
        if not analysis_file or not os.path.exists(analysis_file):
            return {"status": "error", "message": "Video no encontrado en la DB"}
            
        with open(analysis_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            
        for c in data.get("completed_proposals", []):
            if c["id"] == req.clip_id:
                c["is_published"] = True
                break
                
        with open(analysis_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)
            
        return {"status": "success", "message": "Marcado como subido"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

class UpdatePublishDatesRequest(BaseModel):
    clip_id: str
    db_file: str
    pub_yt: str
    pub_ig: str
    pub_tiktok: str

@app.post("/update_publish_dates")
def update_publish_dates(req: UpdatePublishDatesRequest):
    try:
        filepath = os.path.join(DB_DIR, req.db_file)
        if not os.path.exists(filepath):
            return {"status": "error", "message": "DB file not found"}
            
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
            
        updated = False
        for c in data.get("completed_proposals", []):
            if c["id"] == req.clip_id:
                c["pub_yt"] = req.pub_yt
                c["pub_ig"] = req.pub_ig
                c["pub_tiktok"] = req.pub_tiktok
                updated = True
                
        if updated:
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
                
        return {"status": "success"}
    except Exception as e:
        return {"status": "error", "message": str(e)}
@app.post("/preview_audio_mix")
@app.get('/get_clip_audio_track')
def get_clip_audio_track(video_name: str, start: float, end: float, track_index: int):
    try:
        video_path = find_video_path(video_name)
        if not video_path:
            return JSONResponse(status_code=404, content={'error': 'Video not found'})
            
        import os, tempfile, subprocess
        
        # Track 1 is index 1, Track 2 is index 2 in ffmpeg 0:a:1 and 0:a:2
        temp_dir = os.path.join(os.getcwd(), 'temp_clips')
        os.makedirs(temp_dir, exist_ok=True)
        
        out_path = os.path.join(temp_dir, f'audio_track_{track_index}_{start}_{end}.mp3')
        
        if not os.path.exists(out_path):
            cmd = [
                'ffmpeg', '-y', '-hide_banner', '-loglevel', 'error',
                '-ss', str(start), '-to', str(end),
                '-i', video_path,
                '-map', f'0:a:{track_index}',
                '-q:a', '5',
                out_path
            ]
            subprocess.run(cmd, check=True)
            
        return FileResponse(out_path)
    except Exception as e:
        print('Error extracting track:', e)
        return JSONResponse(status_code=500, content={'error': str(e)})


def preview_audio_mix(req: AudioPreviewRequest):
    try:
        video_path = os.path.join(VIDEO_DIR, req.video_name)
        if not os.path.exists(video_path):
            return {"status": "error", "message": "Video not found"}
            
        duration = req.end - req.start
        
        # 0-indexed tracks in ffmpeg. User sends 1-indexed.
        tv = req.track_voz - 1
        tj = req.track_juego - 1
        
        preview_filename = f"preview_mix_{req.start}_{req.end}_{req.vol_voz}_{req.vol_juego}.mp3"
        preview_path = os.path.join(TEMP_DIR, preview_filename)
        
        if not os.path.exists(preview_path):
            # Mix the two tracks with volume
            cmd = [
                "ffmpeg", "-y", 
                "-ss", str(req.start), 
                "-i", video_path, 
                "-t", str(duration),
                "-filter_complex", f"[0:a:{tv}]volume={req.vol_voz}[a1];[0:a:{tj}]volume={req.vol_juego}[a2];[a1][a2]amix=inputs=2:duration=first:dropout_transition=0[a]",
                "-map", "[a]",
                "-b:a", "128k",
                preview_path
            ]
            subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
        return {"status": "success", "url": f"/temp/{preview_filename}"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host='0.0.0.0', port=8000)

