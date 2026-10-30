
# === OPTIMIZACIÓN DE RECURSOS Y TEMPERATURA (ANTI-FREEZE) ===
try:
    import psutil
    psutil.Process().nice(psutil.BELOW_NORMAL_PRIORITY_CLASS)
except Exception:
    pass

try:
    import torch
    # Limitar PyTorch a 4 hilos en vez de los 14 núcleos de la laptop para evitar congelamiento de Windows
    torch.set_num_threads(4)
except Exception:
    pass

from fastapi import FastAPI, HTTPException, BackgroundTasks, Header, Request, UploadFile, File
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

def atomic_write_json(file_path, data):
    import tempfile
    import os
    import json
    dir_name = os.path.dirname(file_path)
    if not os.path.exists(dir_name):
        os.makedirs(dir_name, exist_ok=True)
    with tempfile.NamedTemporaryFile('w', dir=dir_name, delete=False, encoding='utf-8') as tf:
        json.dump(data, tf, indent=4, ensure_ascii=False)
        temp_name = tf.name
    os.replace(temp_name, file_path)


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
HTML_FILE = os.path.join(os.path.dirname(__file__), "templates", "index.html")
FFMPEG_BIN = r"C:\Users\leone\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1.1-full_build\bin\ffmpeg.exe"

os.makedirs(TEMP_CLIPS_DIR, exist_ok=True)

class UpdateClipRequest(BaseModel):
    clip_id: str
    ass_text: str
    video_name: str
    words: list = []
    social_title: Optional[str] = None
    social_desc: Optional[str] = None
    yt_tags: Optional[str] = None
    start: Optional[float] = None
    end: Optional[float] = None
    export_name: Optional[str] = None
    subtitle_style: dict = {}
    cropState: Optional[dict] = None
    stickers: list = []

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
    voice_offset: float = 0.0
    track_voz: int = 2
    track_juego: int = 3

class AudioPreviewRequest(BaseModel):
    video_name: str
    start: float
    end: float
    vol_voz: float = 1.0
    vol_juego: float = 1.0
    voice_offset: float = 0.0
    track_voz: int = 2
    track_juego: int = 3

class GenerateClipsRequest(BaseModel):
    prompt: str
    video_name: str
    search_modes: list[str] = ["volume"]
    max_clips: int = 6
    start_time_str: str = ""
    end_time_str: str = ""
    keywords: str = ""

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

class RegenerateMetadataRequest(BaseModel):
    video_name: str
    transcript: str

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
            response = HTMLResponse(content=html)
            response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
            return response
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
    atomic_write_json(rev_file, data)
    return {"status": "success"}

app.mount('/videos', StaticFiles(directory=VIDEO_DIR), name='videos')

@app.get("/ping")
def ping():
    return {"status": "ok"}

def get_clean_game_name(video_name: str) -> str:
    if not video_name:
        return "Juego"
    norm = video_name.replace("\\", "/").strip("/")
    parts = [p.strip() for p in norm.split("/") if p.strip()]
    if len(parts) > 1 and parts[0].lower() not in ("gourmet", "raiz", "raíz"):
        raw_game = parts[0]
    else:
        base = os.path.splitext(parts[-1])[0] if parts else "Juego"
        # Quitar fechas de OBS como " - 2026-06-21_19-18-16"
        base = re.sub(r'\s*-\s*\d{4}-\d{2}-\d{2}[_\s]\d{2}-\d{2}-\d{2}.*$', '', base)
        # Quitar sufijos de stream/resumen como "Resumen", "Directo 1...", "Leito..."
        base = re.sub(r'(?i)[\s_-]+(resumen|directo\s*\d*|leito.*|final.*)$', '', base)
        # Quitar número de episodio con guion bajo al final (ej: WalkingDead_1 -> WalkingDead)
        base = re.sub(r'_+\d+$', '', base)
        raw_game = base.strip() or "Juego"
    clean = re.sub(r'[^a-zA-Z0-9]+', '_', raw_game).strip('_')
    return clean or "Juego"

def sync_clip_id_with_export_name(data: dict, clip_id: str, export_name: Optional[str]) -> str:
    if not export_name:
        return clip_id
    clean_exp = export_name.strip()
    if clean_exp.lower().endswith(".mp4"):
        clean_exp = clean_exp[:-4]
    m = re.match(r'^(\d+)_', clean_exp)
    if not m:
        return clip_id
    global_num = int(m.group(1))
    new_id = f"clip_{global_num}"

    proposals = data.get("proposals", [])
    completed = data.get("completed_proposals", [])
    rejected = data.get("rejected_proposals", [])
    all_lists = [proposals, completed, rejected]

    target_clip = None
    for lst in (proposals, completed):
        for c in lst:
            if c.get("id") == clip_id:
                target_clip = c
                break
        if target_clip:
            break
    if not target_clip:
        for lst in (proposals, completed):
            for c in lst:
                if c.get("export_name") == clean_exp or c.get("id") == new_id:
                    target_clip = c
                    break
            if target_clip:
                break

    if not target_clip:
        return clip_id

    old_id = target_clip.get("id", clip_id)
    target_clip["export_name"] = clean_exp

    if old_id != new_id:
        # Si otro clip pendiente/descartado tenía ese mismo ID local (ej. clip_48), renombrarlo para evitar colisión
        used_ids = {c.get("id") for lst in all_lists for c in lst if c.get("id")}
        for lst in all_lists:
            for c in lst:
                if c is not target_clip and c.get("id") == new_id:
                    fallback_idx = 1000
                    while f"clip_p{fallback_idx}" in used_ids:
                        fallback_idx += 1
                    alt_id = f"clip_p{fallback_idx}"
                    used_ids.add(alt_id)
                    c["id"] = alt_id
                    old_ass_collision = os.path.join(ASS_DIR, f"subs_{new_id}.ass")
                    new_ass_collision = os.path.join(ASS_DIR, f"subs_{alt_id}.ass")
                    if os.path.exists(old_ass_collision) and not os.path.exists(new_ass_collision):
                        try:
                            shutil.copyfile(old_ass_collision, new_ass_collision)
                        except Exception:
                            pass

        old_ass = os.path.join(ASS_DIR, f"subs_{old_id}.ass")
        new_ass = os.path.join(ASS_DIR, f"subs_{new_id}.ass")
        if os.path.exists(old_ass):
            try:
                shutil.copyfile(old_ass, new_ass)
            except Exception:
                pass

        target_clip["id"] = new_id

    return new_id

@app.get("/next_export_info")
def get_next_export_info(video_name: str = "", clip_id: str = ""):
    try:
        clean_game = get_clean_game_name(video_name)
        max_global_num = 0
        completed_game_count = 0
        max_game_suffix = 0
        existing_export_name = None
        existing_global_num = None
        existing_game_count = None

        target_analysis_file = os.path.abspath(get_analysis_file(video_name)) if video_name else ""

        if os.path.exists(DB_DIR):
            for fname in os.listdir(DB_DIR):
                if not fname.endswith(".json") or fname in ("cost_history.json", "feedback_ia.json", "reviewed_videos.json"):
                    continue
                fpath = os.path.abspath(os.path.join(DB_DIR, fname))
                try:
                    with open(fpath, "r", encoding="utf-8") as f:
                        d = json.load(f)
                except Exception:
                    continue
                if not isinstance(d, dict):
                    continue

                v_name = d.get("video", "")
                v_game = get_clean_game_name(v_name)
                is_same_file = (fpath == target_analysis_file)

                # Revisar si el clip actual ya tiene export_name asignado
                if is_same_file and clip_id:
                    for lst_name in ("proposals", "completed_proposals"):
                        for c in d.get(lst_name, []):
                            if c.get("id") == clip_id and c.get("export_name"):
                                exp = c["export_name"].strip()
                                if exp.lower().endswith(".mp4"):
                                    exp = exp[:-4]
                                m_lead = re.match(r'^(\d+)_', exp)
                                m_tail = re.search(r'_(\d+)$', exp)
                                if m_lead:
                                    existing_global_num = int(m_lead.group(1))
                                    existing_game_count = int(m_tail.group(1)) if m_tail else 1
                                    existing_export_name = f"{existing_global_num}_{clean_game}_{existing_game_count}"

                for c in d.get("completed_proposals", []):
                    exp = str(c.get("export_name", "") or "").strip()
                    if exp.lower().endswith(".mp4"):
                        exp = exp[:-4]
                    m_lead = re.match(r'^(\d+)_', exp)
                    if m_lead:
                        g_val = int(m_lead.group(1))
                        if g_val > max_global_num:
                            max_global_num = g_val
                    else:
                        m_id = re.match(r'^clip_(\d+)$', str(c.get("id", "")))
                        if m_id:
                            g_val = int(m_id.group(1))
                            if g_val > max_global_num:
                                max_global_num = g_val

                    if v_game.lower() == clean_game.lower():
                        if is_same_file and c.get("id") == clip_id:
                            continue
                        completed_game_count += 1
                        m_exact = re.match(rf'^\d+_{re.escape(clean_game)}_(\d+)$', exp, re.IGNORECASE)
                        if m_exact:
                            sfx = int(m_exact.group(1))
                            if sfx > max_game_suffix:
                                max_game_suffix = sfx

        # También verificar archivos exportados en EXPORTS_DIR para no repetir nunca un número global
        if os.path.exists(EXPORTS_DIR):
            for root, _, files in os.walk(EXPORTS_DIR):
                for fn in files:
                    if fn.lower().endswith(".mp4"):
                        m_lead = re.match(r'^(\d+)_', fn)
                        if m_lead:
                            g_val = int(m_lead.group(1))
                            if g_val > max_global_num:
                                max_global_num = g_val

        next_game_count = max(completed_game_count, max_game_suffix) + 1
        return {
            "status": "success",
            "game_name": clean_game,
            "game_count": existing_game_count if existing_game_count is not None else next_game_count,
            "next_global_num": max_global_num + 1,
            "existing_export_name": existing_export_name,
            "existing_global_num": existing_global_num
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.get("/thumbnail")
def get_thumbnail(video: str, time: float, export: str = ""):
    # Intento 1: Video Exportado (si existe, para mostrar miniatura final)
    if export:
        candidates = [export] if export.lower().endswith(".mp4") else [export, f"{export}.mp4"]
        export_path = ""
        for cand in candidates:
            p = os.path.join(EXPORTS_DIR, cand)
            if os.path.exists(p):
                export_path = p
                break
        if not export_path:
            # Buscar en subcarpetas (ej: "Subidos")
            for root, dirs, files in os.walk(EXPORTS_DIR):
                for cand in candidates:
                    if cand in files:
                        export_path = os.path.join(root, cand)
                        break
                if export_path:
                    break
                    
        if export_path and os.path.exists(export_path):
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

def run_ffmpeg(cmd, clip_id, total_duration, alias_id=None):
    export_progress[clip_id] = "0"
    if alias_id:
        export_progress[alias_id] = "0"
    total_dur = total_duration
    try:
        below_normal = getattr(subprocess, "BELOW_NORMAL_PRIORITY_CLASS", 0x00004000)
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL, universal_newlines=True, creationflags=below_normal)
        stdout_lines = []
        for line in process.stdout:
            stdout_lines.append(line)
            if "out_time_ms=" in line:
                ms_str = line.strip().split("=")[1]
                if ms_str.isdigit() and total_dur > 0:
                    ms = int(ms_str) / 1000000.0
                    percent = min(99, int((ms / total_dur) * 100))
                    export_progress[clip_id] = str(percent)
                    if alias_id:
                        export_progress[alias_id] = str(percent)
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
        if alias_id:
            export_progress[alias_id] = "100"
    except Exception as e:
        export_progress[clip_id] = "-1"
        if alias_id:
            export_progress[alias_id] = "-1"
        try:
            with open(os.path.join(BASE_DIR, "ffmpeg_error.log"), "w", encoding="utf-8", errors="replace") as f:
                f.write(f"Error en run_ffmpeg: {e}\n{traceback.format_exc()}")
        except Exception as write_err:
            print(f"Failed to write ffmpeg_error.log: {write_err}")

def get_video_recording_window(video_path: str):
    """
    Calcula la ventana real (inicio, fin, duracion_seg) en que se grabó un video en OBS,
    incluso si el archivo fue movido de C: a D:, renombrado con prefijo 'Juego_N - YYYY-MM-DD HH-MM-SS',
    o remuxeado de .mkv a .mp4 al terminar el stream.
    """
    import datetime
    import subprocess

    stat = os.stat(video_path)
    ctime = datetime.datetime.fromtimestamp(stat.st_ctime)
    mtime = datetime.datetime.fromtimestamp(stat.st_mtime)

    dur_sec = 0.0
    try:
        ffprobe_bin = FFMPEG_BIN.replace("ffmpeg.exe", "ffprobe.exe") if "ffmpeg.exe" in FFMPEG_BIN.lower() else "ffprobe"
        out = subprocess.check_output(
            [ffprobe_bin, "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", video_path],
            stderr=subprocess.DEVNULL
        ).decode("utf-8", errors="ignore").strip()
        dur_sec = float(out)
    except Exception:
        dur_sec = 0.0

    bname = os.path.basename(video_path)
    # 1. Prioridad máxima: fecha y hora de OBS en el nombre (ej: Juego_1 - 2026-10-24 21-05-51.mp4)
    m = re.search(r"(20\d{2}-\d{2}-\d{2})[\s_-]*(\d{2}-\d{2}-\d{2})", bname)
    if m:
        try:
            start_dt = datetime.datetime.strptime(f"{m.group(1)} {m.group(2).replace('-', ':')}", "%Y-%m-%d %H:%M:%S")
            if dur_sec > 0:
                end_dt = start_dt + datetime.timedelta(seconds=dur_sec)
            else:
                end_dt = max(mtime, start_dt)
            return start_dt, end_dt, dur_sec
        except Exception:
            pass

    # 2. Fallback si se borró la fecha del nombre: usar duración real de ffprobe + mtime/ctime
    if dur_sec > 0:
        span_fs = (mtime - ctime).total_seconds()
        if ctime > mtime or abs(span_fs - dur_sec) < 900:
            end_dt = mtime
            start_dt = end_dt - datetime.timedelta(seconds=dur_sec)
            return start_dt, end_dt, dur_sec
        elif 0 <= span_fs < dur_sec * 0.4:
            # Remuxeado a .mp4 justo al terminar de grabar
            end_dt = ctime
            start_dt = end_dt - datetime.timedelta(seconds=dur_sec)
            return start_dt, end_dt, dur_sec

    return min(ctime, mtime), max(ctime, mtime), dur_sec


def sync_streamdeck_markers(video_name: str, data: dict = None, analysis_file: str = None) -> dict:
    """
    Sincroniza los marcadores manuales de db/markers.txt que correspondan a la ventana real de grabación
    del video, sin importar si fue movido de C: a D:, renombrado o pasado a .mp4.
    """
    import datetime
    from pipeline import extract_game_title

    if not video_name:
        return data or {}

    if analysis_file is None:
        analysis_file = get_analysis_file(video_name)
    if data is None:
        if analysis_file and os.path.exists(analysis_file):
            with open(analysis_file, "r", encoding="utf-8") as f:
                data = json.load(f)
        else:
            data = {"video": video_name, "proposals": [], "completed_proposals": [], "completed_ranges": [], "rejected_proposals": []}

    markers_file = os.path.join(DB_DIR, "markers.txt")
    if not os.path.exists(markers_file):
        return data

    video_path = find_video_path(video_name)
    if not video_path or not os.path.exists(video_path):
        return data

    try:
        video_start_time, video_end_time, dur_sec = get_video_recording_window(video_path)
        with open(markers_file, "r", encoding="utf-8") as f:
            markers_lines = [ln.strip() for ln in f if ln.strip()]

        synced_set = set(data.get("synced_markers", []))
        all_existing = (
            data.get("proposals", [])
            + data.get("completed_proposals", [])
            + data.get("rejected_proposals", [])
            + data.get("archived_proposals", [])
        )

        max_id_val = 0
        for ex in all_existing:
            if str(ex.get("id", "")).startswith("clip_"):
                try:
                    num = int(ex["id"].split("_")[1])
                    if num > max_id_val:
                        max_id_val = num
                except Exception:
                    pass

        game_title = extract_game_title(video_name)
        added_any = False
        last_marker_rel = -999.0

        for line in markers_lines:
            raw_ts = line.split("|")[0].strip()
            if raw_ts in synced_set:
                continue
            try:
                marker_time = datetime.datetime.strptime(raw_ts, "%Y-%m-%d %H:%M:%S")
            except Exception:
                continue

            if video_start_time <= marker_time <= video_end_time:
                rel_seconds = (marker_time - video_start_time).total_seconds()
                synced_set.add(raw_ts)

                # Ignorar doble click del botón de Streamdeck en menos de 15 segundos
                if abs(rel_seconds - last_marker_rel) < 15.0:
                    added_any = True
                    continue
                last_marker_rel = rel_seconds

                # Cuando presionás el botón en vivo, la acción acaba de ocurrir (40s antes a 20s después)
                c_start = round(max(0.0, rel_seconds - 40.0), 2)
                c_end = round(min(dur_sec if dur_sec > 0 else rel_seconds + 20.0, rel_seconds + 20.0), 2)
                if c_end - c_start < 20.0:
                    c_end = round(c_start + 35.0, 2)

                # Verificar si ya existe un clip manual/aprobado/rechazado en ese mismo momento
                already_covered = False
                for p in all_existing:
                    ps, pe = float(p.get("start", 0)), float(p.get("end", 0))
                    if p.get("category") == "manual" and max(c_start, ps) < min(c_end, pe):
                        already_covered = True
                        break
                    if ps <= rel_seconds <= pe:
                        already_covered = True
                        break

                if already_covered:
                    added_any = True
                    continue

                max_id_val += 1
                mm = int(rel_seconds // 60)
                ss = int(rel_seconds % 60)
                hh = mm // 60
                mm_rem = mm % 60
                t_label = f"{hh:02d}:{mm_rem:02d}:{ss:02d}" if hh > 0 else f"{mm_rem:02d}:{ss:02d}"

                c = {
                    "id": f"clip_{max_id_val}",
                    "start": c_start,
                    "end": c_end,
                    "category": "manual",
                    "is_streamdeck": True,
                    "marker_sec": round(rel_seconds, 2),
                    "needs_ai_refine": True,
                    "reason": f"📌 Marcador manual Streamdeck (marcado en {t_label})",
                    "virality_score": 100,
                    "transcript": "Marcador insertado manualmente durante la grabación.",
                    "social_title": f"Momento en {game_title}",
                    "social_desc": f"Jugando a {game_title} pasó esto en directo. #{re.sub(r'[^a-zA-Z0-9]', '', game_title.title())} #Leito4Gaming #Gaming",
                    "yt_title": f"Momento en {game_title}",
                    "yt_desc": f"Jugando a {game_title} en vivo.",
                    "yt_tags": f"Leito4Gaming, Leito4GamingPlus, {game_title}, gameplay español, shorts",
                    "template": "face_game",
                    "cropState": {
                        "splitY": 960,
                        "face": {"x": 58, "y": 808, "w": 384, "h": 216},
                        "game": {"x": 0, "y": 0, "w": 1920, "h": 1080},
                        "full": {"x": 0, "y": 0, "w": 1920, "h": 1080},
                        "subs": {"x": 530, "y": 744, "w": 860, "h": 336}
                    }
                }
                data.setdefault("proposals", []).append(c)
                all_existing.append(c)
                added_any = True

        for p in data.get("proposals", []):
            r_low = str(p.get("reason", "")).lower()
            t_low = str(p.get("transcript", "")).lower()
            if "streamdeck" in r_low or "marcador manual" in r_low or "insertado manualmente" in t_low:
                if p.get("category") != "manual":
                    p["category"] = "manual"
                    added_any = True
                if "insertado manualmente" in t_low and "needs_ai_refine" not in p:
                    p["needs_ai_refine"] = True
                    added_any = True

        if added_any:
            data["synced_markers"] = sorted(synced_set)
            data["proposals"].sort(key=lambda x: x.get("start", 0))
            if analysis_file:
                atomic_write_json(analysis_file, data)
    except Exception as e_mk:
        print(f"Error en sync_streamdeck_markers para {video_name}: {e_mk}")

    return data


@app.get("/clips")
def get_clips(video_name: str = ""):
    try:
        analysis_file = get_analysis_file(video_name)
        if not analysis_file:
            return {"status": "success", "data": {"clips": [], "completed_clips": [], "video_name": video_name}}

        if os.path.exists(analysis_file):
            with open(analysis_file, "r", encoding="utf-8") as f:
                data = json.load(f)
        else:
            data = {"video": video_name, "proposals": [], "completed_proposals": [], "completed_ranges": [], "rejected_proposals": []}

        # Sincronizar automáticamente marcadores de Streamdeck aunque el video haya sido movido de C: a D: o renombrado
        data = sync_streamdeck_markers(video_name, data, analysis_file)
            
        proposals_raw = data.get("proposals", [])
        
        # Filtro de Calidad SemÃƒÂ¡ntico
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
            "archived_clips": data.get("archived_proposals", []),
            "video_name": video_name
        }}
        
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.post("/generate_clips")
def generate_clips(req: GenerateClipsRequest, background_tasks: BackgroundTasks):
    if analysis_progress.get("status") == "processing":
        return {"status": "error", "message": "Ya hay un proceso de generación en curso. Espera a que termine."}
    
    background_tasks.add_task(_generate_clips_task, req)
    return {"status": "success", "message": "Generación iniciada en segundo plano."}

def _generate_clips_task(req: GenerateClipsRequest):
    try:
        import time
        import uuid
        import subprocess
        import re
        import datetime
        
        video_file_name = req.video_name
        if not video_file_name:
            analysis_progress["status"] = "error"
            analysis_progress["message"] = "No hay video activo."
            return
            
        analysis_file = get_analysis_file(video_file_name)
        data = {"video": video_file_name, "proposals": [], "completed_proposals": [], "completed_ranges": []}
        if analysis_file and os.path.exists(analysis_file):
            with open(analysis_file, "r", encoding="utf-8") as f:
                data = json.load(f)
        
        data["video"] = video_file_name
        if analysis_file:
            atomic_write_json(analysis_file, data)
            
        video_path = find_video_path(video_file_name)
        if not os.path.exists(video_path):
            analysis_progress["status"] = "error"
            analysis_progress["message"] = f"Video no encontrado: {video_path}"
            return
            
        gemini_api_key = ""
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                gemini_api_key = json.load(f).get("gemini_api_key", "")
                
        if not gemini_api_key:
            analysis_progress["status"] = "error"
            analysis_progress["message"] = "No se ha configurado la API Key de Gemini en los ajustes."
            return
            
        try:
            import pipeline
            import importlib
            importlib.reload(pipeline)
            from pipeline import analyze_video_local_first, analyze_video_semantic
        except ImportError:
            analysis_progress["status"] = "error"
            analysis_progress["message"] = "Falta el archivo pipeline.py."
            return
            
        def progress_cb(percent, msg):
            analysis_progress["percent"] = percent
            analysis_progress["message"] = msg
            
        analysis_progress["status"] = "processing"
        analysis_progress["percent"] = 5
        analysis_progress["message"] = "Iniciando anÃƒÂ¡lisis..."
            
        def parse_time(t_str, default):
            if not t_str: return default
            parts = t_str.split(':')
            try:
                if len(parts) == 3:
                    return int(parts[0])*3600 + int(parts[1])*60 + int(parts[2])
                elif len(parts) == 2:
                    return int(parts[0])*60 + int(parts[1])
                elif len(parts) == 1:
                    return int(parts[0])
            except:
                return default
            return default
            
        range_start = parse_time(req.start_time_str, 0)
        range_end = parse_time(req.end_time_str, 999999)
        
        # Recopilar zonas a excluir (clips ya generados o completados)
        exclusion_zones = []
        if range_start > 0:
            exclusion_zones.append((0, range_start))
        if range_end < 999999:
            exclusion_zones.append((range_end, 999999))
            
        max_id_val = 0
        all_existing = data.get("proposals", []) + data.get("completed_proposals", []) + data.get("rejected_proposals", [])
        for ex in all_existing:
            if str(ex.get("id", "")).startswith("clip_"):
                try:
                    num = int(ex["id"].split("_")[1])
                    if num > max_id_val: max_id_val = num
                except:
                    pass
        
        saved_clips_count = 0
        def incremental_save(c):
            nonlocal max_id_val, saved_clips_count
            s, e = c['start'], c['end']
            overlap = False
            for p in data.get("proposals", []) + data.get("completed_proposals", []) + data.get("completed_ranges", []) + data.get("rejected_proposals", []):
                if max(s, p['start']) < min(e, p['end']): overlap = True
            if overlap: return
            if "archived_proposals" in data:
                data["archived_proposals"] = [
                    ap for ap in data["archived_proposals"]
                    if not (max(s, ap.get("start", 0)) < min(e, ap.get("end", 0)))
                ]

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
            saved_clips_count += 1
            if analysis_file:
                atomic_write_json(analysis_file, data)
                    
        # Procesar chat (Streamer.bot o TwitchDownloader)
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
                                "category": "chat",
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
                video_start_time, video_end_time, _ = get_video_recording_window(video_path)
                
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
                            "category": "chat",
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

        # Procesar marcadores de Streamdeck (usando fecha en nombre + duración real de ffprobe)
        data = sync_streamdeck_markers(video_file_name, data, analysis_file)

        all_new_clips = []
        total_in = 0
        total_out = 0

        # Si hay marcas manuales de Streamdeck sin analizar por la IA, usarlas como guía VIP para encuadrar y titular
        unrefined_manuals = [
            p for p in data.get("proposals", [])
            if p.get("category") == "manual" and (
                p.get("needs_ai_refine") or "insertado manualmente" in str(p.get("transcript", "")).lower()
            )
        ]
        if unrefined_manuals:
            try:
                from pipeline import refine_manual_markers
                m_in, m_out = refine_manual_markers(video_path, unrefined_manuals, gemini_api_key, TEMP_CLIPS_DIR, progress_cb)
                total_in += m_in
                total_out += m_out
                data["proposals"].sort(key=lambda x: x.get("start", 0))
                if analysis_file:
                    atomic_write_json(analysis_file, data)
            except Exception as e_mref:
                print(f"Aviso en refine_manual_markers: {e_mref}")

        for p in data.get("proposals", []):
            exclusion_zones.append((p.get("start", 0), p.get("end", 0)))
        for p in data.get("completed_proposals", []):
            exclusion_zones.append((p.get("start", 0), p.get("end", 0)))
        for p in data.get("completed_ranges", []):
            exclusion_zones.append((p.get("start", 0), p.get("end", 0)))
        for p in data.get("rejected_proposals", []):
            exclusion_zones.append((p.get("start", 0), p.get("end", 0)))

        # === TORNEO ESCALADO POR DURACIÓN DEL VIDEO ===
        _, _, video_dur_sec = get_video_recording_window(video_path)
        if req.max_clips and req.max_clips > 0:
            final_n = req.max_clips
        else:
            if video_dur_sec >= 8400:      # > 2h 20m
                final_n = 15
            elif video_dur_sec >= 5100:    # 1h 25m a 2h 20m (~2 horas)
                final_n = 12
            elif video_dur_sec >= 2700:    # 45m a 1h 25m
                final_n = 9
            else:                          # < 45m
                final_n = 6
        candidate_budget = max(24, int(final_n * 2.2))
        candidate_pool = []

        def collect_candidate(c):
            cs, ce = c.get("start", 0), c.get("end", 0)
            for p in data.get("proposals", []) + data.get("completed_proposals", []) + data.get("completed_ranges", []) + data.get("rejected_proposals", []):
                if max(cs, p.get("start", 0)) < min(ce, p.get("end", 0)):
                    return
            candidate_pool.append(c)
            # Persistir el pool por si se corta el proceso
            data["candidate_pool"] = candidate_pool
            if analysis_file:
                atomic_write_json(analysis_file, data)

        if "volume" in req.search_modes:
            print("Iniciando Pipeline de Ahorro de Tokens Local-First...")
            def prog_vol(pct, msg): progress_cb(int(pct * 0.45), "MODO ACCIÓN: " + msg) if "semantic" in req.search_modes else progress_cb(int(pct * 0.9), msg)
            nc, tin, tout = analyze_video_local_first(
                video_path, req.prompt, gemini_api_key, TEMP_CLIPS_DIR, prog_vol, exclusion_zones, collect_candidate, candidate_budget
            )
            all_new_clips.extend(nc)
            total_in += tin
            total_out += tout
            for p in nc: exclusion_zones.append((p.get("start", 0), p.get("end", 0)))

        if "semantic" in req.search_modes:
            print("Iniciando Pipeline Semántico (Whisper + Gemini Texto)")
            def prog_sem(pct, msg): progress_cb(45 + int(pct * 0.45), "MODO HISTORIA: " + msg) if "volume" in req.search_modes else progress_cb(int(pct * 0.9), msg)
            nc, tin, tout = analyze_video_semantic(
                video_path, req.prompt, gemini_api_key, TEMP_CLIPS_DIR, prog_sem, exclusion_zones,
                collect_candidate, candidate_budget, req.keywords
            )
            all_new_clips.extend(nc)
            total_in += tin
            total_out += tout

        winners, losers = [], []
        if candidate_pool:
            progress_cb(93, f"🏆 Torneo final: eligiendo los {final_n} mejores de {len(candidate_pool)} candidatos...")
            from pipeline import rank_and_select_best
            winners, losers, rin, rout = rank_and_select_best(
                candidate_pool, gemini_api_key, os.path.basename(video_path), top_n=final_n
            )
            total_in += rin
            total_out += rout
            for w in sorted(winners, key=lambda x: x["start"]):
                w.pop("_source", None); w.pop("_spike", None)
                incremental_save(w)
            archived = data.setdefault("archived_proposals", [])
            for l in losers:
                l.pop("_source", None); l.pop("_spike", None)
                l["id"] = "arch_" + uuid.uuid4().hex[:6]
                l["archived_reason"] = "No entró en el top: " + str(l.get("rank_why", ""))
                archived.append(l)
        data.pop("candidate_pool", None)
        if analysis_file:
            atomic_write_json(analysis_file, data)
        all_new_clips = winners

        analysis_progress["status"] = "idle"
        
        # Guardar costos (Gemini Flash-Lite: $0.10/1M texto, ~$0.30/1M audio, $0.40/1M salida)
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
        
        input_rate = 0.20 if "volume" in req.search_modes else 0.10
        cost_in = (total_in / 1_000_000) * input_rate
        cost_out = (total_out / 1_000_000) * 0.40
        costs_data[current_month]["cost"] += (cost_in + cost_out)
        
        atomic_write_json(COSTS_FILE, costs_data)
        
        if not all_new_clips and saved_clips_count == 0:
            analysis_progress["status"] = "idle"
            analysis_progress["message"] = "No se encontraron clips nuevos."
            return {"status": "error", "message": "No se encontraron clips viables o la IA rechazó los segmentos detectados."}
            
        extra = f" (de {len(candidate_pool)} candidatos; {len(losers)} quedaron archivados)" if candidate_pool else ""
        analysis_progress["message"] = f"🏆 {saved_clips_count} mejores clips elegidos{extra}"
        return {"status": "success", "message": f"🏆 {saved_clips_count} mejores clips elegidos{extra}"}
    except Exception as e:
        err_msg = str(e)
        if "spending cap" in err_msg.lower() or "ai.studio/spend" in err_msg.lower():
            err_msg = "TOPE DE GASTO MENSUAL ALCANZADO: Tu proyecto en Google AI Studio superó el límite de gasto mensual ('Monthly Spend Cap'). Entra a https://ai.studio/spend para subir tu tope mensual o usa otra API Key en Ajustes."
        elif "prepayment credits are depleted" in err_msg or "402" in err_msg:
            err_msg = "CRÉDITOS AGOTADOS (Error 402): Te has quedado sin saldo prepago en Google AI Studio. Recarga saldo en https://ai.studio/projects para poder seguir analizando."
        elif "limit: 0" in err_msg:
            err_msg = "CUOTA AGOTADA: Has superado el límite de tu API Key de Gemini."
        if 'saved_clips_count' in locals() and saved_clips_count > 0:
            err_msg = f"⚠️ Se guardaron {saved_clips_count} clips nuevos con éxito, pero el análisis se detuvo antes de terminar:\n\n{err_msg}"
        analysis_progress["status"] = "error"
        analysis_progress["message"] = err_msg
        print(f"Error crítico en _generate_clips_task: {err_msg}")
        return {"status": "error", "message": err_msg}

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
            "category": "manual",
            "reason": "Clip añadido manualmente",
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
            atomic_write_json(analysis_file, data)
                
        return {"status": "success", "message": "Clip manual aÃƒÂ±adido", "clip_id": clip_id}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.post("/mark_clip_done")
def mark_clip_done(req: MarkClipDoneRequest):
    try:
        import csv
        import datetime
        analysis_file = get_analysis_file(req.video_name)
        if not analysis_file:
            return {"status": "error", "message": "Nombre de video invalido"}
            
        if not os.path.exists(analysis_file):
            data = {"video": req.video_name, "proposals": [], "completed_proposals": [], "completed_ranges": [], "rejected_proposals": []}
        else:
            with open(analysis_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            
        completed_ranges = data.get("completed_ranges", [])
        proposals = data.get("proposals", [])
        completed_proposals = data.get("completed_proposals", [])
        
        target_clip = next((c for c in proposals if c["id"] == req.clip_id), None)
        is_completed = False
        
        if not target_clip:
            target_clip = next((c for c in completed_proposals if c["id"] == req.clip_id), None)
            is_completed = True if target_clip else False

        if not target_clip and req.export_name:
            clean_exp = req.export_name.strip()
            if clean_exp.lower().endswith(".mp4"):
                clean_exp = clean_exp[:-4]
            m_lead = re.match(r'^(\d+)_', clean_exp)
            cand_id = f"clip_{int(m_lead.group(1))}" if m_lead else None
            target_clip = next((c for c in proposals if c.get("export_name") == clean_exp or (cand_id and c.get("id") == cand_id)), None)
            if not target_clip:
                target_clip = next((c for c in completed_proposals if c.get("export_name") == clean_exp or (cand_id and c.get("id") == cand_id)), None)
                is_completed = True if target_clip else False
            
        final_clip_id = req.clip_id
        if target_clip:
            old_id = target_clip["id"]
            target_clip.setdefault("original_ai_transcript", target_clip.get("transcript", ""))
            target_clip.setdefault("original_ai_start", target_clip.get("start", 0))
            target_clip.setdefault("original_ai_end", target_clip.get("end", 0))
            if req.start is not None:
                target_clip["start"] = req.start
            if req.end is not None:
                target_clip["end"] = req.end
            if req.export_name is not None and str(req.export_name).strip():
                final_clip_id = sync_clip_id_with_export_name(data, old_id, req.export_name)
            else:
                final_clip_id = old_id
            
            if not is_completed:
                completed_ranges.append({"start": target_clip["start"], "end": target_clip["end"]})
                data["completed_ranges"] = completed_ranges
                
                # Save full clip to completed_proposals
                completed_proposals = data.get("completed_proposals", [])
                if not any(c is target_clip for c in completed_proposals):
                    completed_proposals.append(target_clip)
                data["completed_proposals"] = completed_proposals
                
                data["proposals"] = [c for c in data.get("proposals", []) if c is not target_clip and c["id"] not in (old_id, final_clip_id)]
            
            atomic_write_json(analysis_file, data)
                
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
                writer.writerow([now, video_src, final_clip_id, export_name, target_clip.get('reason', ''), target_clip['start'], target_clip['end'], dur])
                
        return {"status": "success", "clip_id": final_clip_id}
    except Exception as e:
        return {"status": "error", "message": str(e)}

class RestoreClipRequest(BaseModel):
    clip_id: str
    video_name: str

@app.post("/restore_clip")
def restore_clip(req: RestoreClipRequest):
    try:
        analysis_file = get_analysis_file(req.video_name)
        if not analysis_file:
            return {"status": "error", "message": "Nombre de video invalido"}
            
        if not os.path.exists(analysis_file):
            data = {"video": req.video_name, "proposals": [], "completed_proposals": [], "completed_ranges": [], "rejected_proposals": []}
        else:
            with open(analysis_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            
        completed_proposals = data.get("completed_proposals", [])
        rejected_proposals = data.get("rejected_proposals", [])
        proposals = data.get("proposals", [])
        
        target = next((c for c in completed_proposals if c["id"] == req.clip_id), None)
        if not target:
            target = next((c for c in rejected_proposals if c["id"] == req.clip_id), None)
        archived_proposals = data.get("archived_proposals", [])
        if not target:
            target = next((c for c in archived_proposals if c["id"] == req.clip_id), None)
            if target:
                target.pop("archived_reason", None)
                max_n = 0
                for ex in data.get("proposals", []) + completed_proposals + rejected_proposals:
                    m = re.match(r"^clip_(\d+)$", str(ex.get("id", "")))
                    if m: max_n = max(max_n, int(m.group(1)))
                data["archived_proposals"] = [c for c in archived_proposals if c is not target]
                target["id"] = f"clip_{max_n + 1}"
                req.clip_id = target["id"]
            
        if target:
            proposals.append(target)
            data["proposals"] = proposals
            data["completed_proposals"] = [c for c in completed_proposals if c["id"] != req.clip_id]
            data["rejected_proposals"] = [c for c in rejected_proposals if c["id"] != req.clip_id]
            
            # Quitar de completed_ranges si es posible
            completed_ranges = data.get("completed_ranges", [])
            data["completed_ranges"] = [cr for cr in completed_ranges if not (cr["start"] == target["start"] and cr["end"] == target["end"])]
            
            atomic_write_json(analysis_file, data)
                
        return {"status": "success"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.get("/taste_profile")
def taste_profile(refresh: bool = False):
    try:
        import pipeline, importlib
        importlib.reload(pipeline)
        api_key = ""
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                api_key = json.load(f).get("gemini_api_key", "")
        profile = pipeline.get_taste_profile(api_key, force=refresh)
        meta = {}
        pf = os.path.join(DB_DIR, "taste_profile.json")
        if os.path.exists(pf):
            with open(pf, "r", encoding="utf-8") as f:
                meta = json.load(f)
        return {"status": "success", "profile": profile, "meta": {k: v for k, v in meta.items() if k != "profile"}}
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

            try:
                fb_file_json = os.path.join(DB_DIR, "feedback_ia.json")
                feedback_data = []
                if os.path.exists(fb_file_json):
                    with open(fb_file_json, "r", encoding="utf-8") as fb_f:
                        try:
                            feedback_data = json.load(fb_f)
                        except Exception:
                            feedback_data = []
                fb_key = f"{req.video_name}_{req.clip_id}"
                feedback_data = [item for item in feedback_data if item.get("id") not in (req.clip_id, fb_key)]
                feedback_data.append({
                    "id": fb_key,
                    "feedback": "down",
                    "category": target_clip.get("category", ""),
                    "reason": target_clip.get("reason", ""),
                    "transcript": target_clip.get("transcript", "")
                })
                atomic_write_json(fb_file_json, feedback_data)
            except Exception as fb_err:
                print(f"Aviso guardando feedback de rechazo: {fb_err}")
            
        data["proposals"] = [c for c in proposals if c["id"] != req.clip_id]
        
        atomic_write_json(analysis_file, data)
            
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
            atomic_write_json(analysis_file, data)
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
                    
            atomic_write_json(analysis_file, data)
                
            if target_clip:
                # Guardar en CSV original
                fb_file_csv = os.path.join(DB_DIR, "feedback_ia.csv")
                file_exists = os.path.isfile(fb_file_csv)
                with open(fb_file_csv, 'a', newline='', encoding='utf-8-sig') as f:
                    writer = csv.writer(f)
                    if not file_exists:
                        writer.writerow(['Clip ID', 'Razon original', 'Feedback'])
                    writer.writerow([req.clip_id, target_clip.get('reason', ''), req.feedback])
                
                # Guardar en JSON para InyecciÃƒÂ³n en IA
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
                
                atomic_write_json(fb_file_json, feedback_data)
                    
        return {"status": "success"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.post("/update_clip")
def update_clip(req: UpdateClipRequest):
    try:
        ass_path = os.path.join(ASS_DIR, f"subs_{req.clip_id}.ass")
        with open(ass_path, "w", encoding="utf-8") as f:
            f.write(req.ass_text)
            
        final_clip_id = req.clip_id
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
                    if getattr(req, "yt_tags", None) is not None:
                        c["yt_tags"] = req.yt_tags
                    if req.start is not None:
                        c["start"] = req.start
                    if req.end is not None:
                        c["end"] = req.end
                    if req.export_name is not None:
                        c["export_name"] = req.export_name
                    if req.cropState is not None:
                        c["cropState"] = req.cropState
                    c["stickers"] = req.stickers
            
            completed_proposals = data.get("completed_proposals", [])
            for c in completed_proposals:
                if c["id"] == req.clip_id:
                    c["words"] = req.words
                    if req.social_title is not None:
                        c["social_title"] = req.social_title
                    if req.social_desc is not None:
                        c["social_desc"] = req.social_desc
                    if getattr(req, "yt_tags", None) is not None:
                        c["yt_tags"] = req.yt_tags
                    if req.start is not None:
                        c["start"] = req.start
                    if req.end is not None:
                        c["end"] = req.end
                    if req.export_name is not None:
                        c["export_name"] = req.export_name
                    if req.cropState is not None:
                        c["cropState"] = req.cropState
                    c["stickers"] = req.stickers
            if req.export_name is not None and str(req.export_name).strip():
                final_clip_id = sync_clip_id_with_export_name(data, req.clip_id, req.export_name)
            atomic_write_json(analysis_file, data)
                
        return {"status": "success", "clip_id": final_clip_id, "message": "SubtÃƒÂ­tulos actualizados correctamente."}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.post("/save_all_clips")
def save_all_clips(req: SaveAllClipsRequest):
    try:
        analysis_file = get_analysis_file(req.video_name)
        if analysis_file:
            if not os.path.exists(analysis_file):
                data = {"video": req.video_name, "proposals": [], "completed_proposals": [], "completed_ranges": [], "rejected_proposals": []}
            else:
                with open(analysis_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
            data["proposals"] = req.proposals
            atomic_write_json(analysis_file, data)
        return {"status": "success"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

class ExportRequest(BaseModel):
    clip_id: str
    start: float
    end: float
    video_name: str
    fit_mode: str
    split_ratio: float = 0.5
    scenes: List[dict]
    hook: Optional[dict] = None
    words: List[dict]
    subtitle_style: dict
    stickers: List[dict] = []
    sounds: List[dict] = []
    outro: Optional[dict] = None
    export_name: Optional[str] = None
    social_title: Optional[str] = None
    social_desc: Optional[str] = None
    social_tags: Optional[str] = None
    export_track: Optional[str] = "mix"
    vol_voz: float = 1.0
    vol_juego: float = 1.0
    voice_offset: float = 0.0
    track_voz: int = 2
    track_juego: int = 3

@app.post("/export")
def export_clip(req: ExportRequest):
    try:
        video_path = find_video_path(req.video_name)
        if not os.path.exists(video_path):
            return {"status": "error", "message": f"Video fuente no encontrado: {video_path}"}
            
        if req.export_name:
            raw_exp = req.export_name.strip()
            if raw_exp.lower().endswith(".mp4"):
                raw_exp = raw_exp[:-4]
            safe_name = "".join(c for c in raw_exp if c.isalnum() or c in " _-").strip()
            if not safe_name: safe_name = req.clip_id + "_render"
            out_file = os.path.join(EXPORTS_DIR, f"{safe_name}.mp4")
        else:
            safe_name = ""
            out_file = os.path.join(EXPORTS_DIR, f"{req.clip_id}_render.mp4")

        # Sincronizar export_name y el ID del clip con el número inicial del archivo exportado
        synced_clip_id = req.clip_id
        if safe_name:
            analysis_file = get_analysis_file(req.video_name)
            if analysis_file and os.path.exists(analysis_file):
                try:
                    with open(analysis_file, "r", encoding="utf-8") as af:
                        adata = json.load(af)
                    synced_clip_id = sync_clip_id_with_export_name(adata, req.clip_id, safe_name)
                    atomic_write_json(analysis_file, adata)
                except Exception as sync_err:
                    print("Advertencia al sincronizar ID en export:", sync_err)
        
        # 1. Generar SubtÃƒÂ­tulos DinÃƒÂ¡micos (.ass)
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

            # AÃƒÂ±adir stickers de texto al archivo ASS
            if req.stickers:
                for st in req.stickers:
                    if st.get("type") == "text":
                        st_start = st.get('start', 0.0)
                        st_end = st.get('end', 0.0)
                        
                        if True:
                                s_ms = int(st_start * 1000)
                                e_ms = int(st_end * 1000)
                                
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
            # Formatear usando la configuraciÃƒÂ³n capturada (o fallback a la primera escena)
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
                
            font_size = int(req.hook.get('fontSize', 65) or 65)
            
            import textwrap
            def wrap_hook_text(raw_text, font_sz):
                if not raw_text or not str(raw_text).strip():
                    return []
                max_chars = max(12, int(1350 / font_sz))
                lines = []
                for paragraph in str(raw_text).splitlines():
                    p = paragraph.strip()
                    if not p:
                        continue
                    wrapped = textwrap.wrap(p, width=max_chars, break_long_words=True)
                    lines.extend(wrapped)
                return lines
                
            top_lines = wrap_hook_text(req.hook.get('textTop', ''), font_size)
            if top_lines:
                line_height = int(font_size * 1.25)
                box_h = int(len(top_lines) * line_height + 30)
                box_y = int(top_y_px - 15)
                draw_pipeline += f",drawbox=y={box_y}:color=black@0.7:width=iw:height={box_h}:t=fill"
                for i_l, l_txt in enumerate(top_lines):
                    esc_txt = l_txt.replace('\\', '\\\\').replace("'", "'\\\\''").replace(":", "\\:").replace("%", "\\%")
                    l_y = int(top_y_px + i_l * line_height)
                    draw_pipeline += f",drawtext=fontfile='{font_path}':text='{esc_txt}':fontcolor={color_choice}:fontsize={font_size}:x=(w-text_w)/2:y={l_y}:shadowcolor=black:shadowx=4:shadowy=4"
            
            bot_lines = wrap_hook_text(req.hook.get('textBottom', ''), font_size)
            if bot_lines:
                line_height = int(font_size * 1.25)
                box_h = int(len(bot_lines) * line_height + 30)
                box_y = int(bottom_y_px - 15)
                draw_pipeline += f",drawbox=y={box_y}:color=black@0.7:width=iw:height={box_h}:t=fill"
                for i_l, l_txt in enumerate(bot_lines):
                    esc_txt = l_txt.replace('\\', '\\\\').replace("'", "'\\\\''").replace(":", "\\:").replace("%", "\\%")
                    l_y = int(bottom_y_px + i_l * line_height)
                    draw_pipeline += f",drawtext=fontfile='{font_path}':text='{esc_txt}':fontcolor={color_choice}:fontsize={font_size}:x=(w-text_w)/2:y={l_y}:shadowcolor=black:shadowx=4:shadowy=4"
                
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
                voice_offset = float(getattr(req, "voice_offset", 0.0) or 0.0)
                s_dur = max(0.05, s_end - s_start)
                for idx_in_valid, (a_idx, vol) in enumerate(valid_tracks):
                    if a_idx == tv and abs(voice_offset) >= 0.005:
                        shifted_start = s_start - voice_offset
                        shifted_end = s_end - voice_offset
                        if shifted_start >= 0.0:
                            filter_parts.append(
                                f"[0:a:{a_idx}]atrim=start={shifted_start:.6f}:end={max(shifted_start + 0.01, shifted_end):.6f},"
                                f"asetpts=PTS-STARTPTS,apad=whole_dur={s_dur:.6f},atrim=0:{s_dur:.6f},volume={vol}[a_s{i}_t{a_idx}]"
                            )
                        else:
                            delay_ms = int(round((-shifted_start) * 1000))
                            trim_end = max(0.01, shifted_end)
                            filter_parts.append(
                                f"[0:a:{a_idx}]atrim=start=0.000000:end={trim_end:.6f},"
                                f"asetpts=PTS-STARTPTS,adelay={delay_ms}:all=1,apad=whole_dur={s_dur:.6f},atrim=0:{s_dur:.6f},volume={vol}[a_s{i}_t{a_idx}]"
                            )
                    else:
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
                voice_offset = float(getattr(req, "voice_offset", 0.0) or 0.0)
                s_dur = max(0.05, s_end - s_start)
                if abs(voice_offset) >= 0.005:
                    shifted_start = s_start - voice_offset
                    shifted_end = s_end - voice_offset
                    if shifted_start >= 0.0:
                        filter_parts.append(
                            f"[0:a:{a_idx}]atrim=start={shifted_start:.6f}:end={max(shifted_start + 0.01, shifted_end):.6f},"
                            f"asetpts=PTS-STARTPTS,apad=whole_dur={s_dur:.6f},atrim=0:{s_dur:.6f},volume={req.vol_voz}[a_s{i}]"
                        )
                    else:
                        delay_ms = int(round((-shifted_start) * 1000))
                        trim_end = max(0.01, shifted_end)
                        filter_parts.append(
                            f"[0:a:{a_idx}]atrim=start=0.000000:end={trim_end:.6f},"
                            f"asetpts=PTS-STARTPTS,adelay={delay_ms}:all=1,apad=whole_dur={s_dur:.6f},atrim=0:{s_dur:.6f},volume={req.vol_voz}[a_s{i}]"
                        )
                else:
                    filter_parts.append(f"[0:a:{a_idx}]atrim=start={s_start:.6f}:end={s_end:.6f},asetpts=PTS-STARTPTS,volume={req.vol_voz}[a_s{i}]")
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
            
            delay_ms = int(snd_start * 1000)
            filter_parts.append(f"[{snd['idx']}:a]adelay={delay_ms}|{delay_ms}[a_snd_{i}]")
            sound_amix_inputs.append(f"[a_snd_{i}]")
        
        if len(sound_amix_inputs) > 1:
            amix_inputs_str = "".join(sound_amix_inputs)
            # weights: 1 para el principal, y 1 para cada sonido
            weights = " ".join(["1"] * len(sound_amix_inputs))
            filter_parts.append(f"{amix_inputs_str}amix=inputs={len(sound_amix_inputs)}:duration=first:dropout_transition=0:weights='{weights}'[a_concat]")
        else:
            filter_parts.append(f"[{current_a}]anull[a_concat]")
        
        # Aplicar SubtÃƒÂ­tulos al video concatenado
        filter_parts.append(f"[v_concat]subtitles='{ass_ff}'[v_subs]")
        
        current_v = "v_subs"
        
        # Aplicar Stickers
        for i, st in enumerate(sticker_inputs):
            scale_w = int(st['w'])
            scale_h = int(st['h'])
            pos_x = int(st['x'])
            pos_y = int(st['y'])
            
            st_start = st['start']
            st_end = st['end']
            
            enable_expr = f"enable='between(t,{st_start},{st_end})'"
            first_s_rel = st_start
            
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
        
        cmd = [FFMPEG_BIN, "-y", "-threads", "8"] + inputs_args + [
            "-filter_complex_threads", "4",
            "-filter_complex", filter_complex,
            "-map", "[v_out]", "-map", "[a_concat]",
            "-c:v", "h264_nvenc", "-preset", "p2", "-cq", "25",
            "-c:a", "aac",
            "-threads", "8",
            "-progress", "pipe:1",
            out_file
        ]
        
        with open(os.path.join(BASE_DIR, "debug_cmd.txt"), "w", encoding="utf-8") as f:
            f.write(repr(cmd))
            
        threading.Thread(target=run_ffmpeg, args=(cmd, req.clip_id, total_dur, synced_clip_id)).start()
        
        # Sanitizar y normalizar metadatos al exportar (sin insultos, con hashtags y tags de YouTube con comas)
        from pipeline import sanitize_and_format_metadata
        meta_temp = {
            "social_title": req.social_title or "",
            "social_desc": req.social_desc or "",
            "yt_tags": getattr(req, "social_tags", None) or "",
        }
        sanitize_and_format_metadata(meta_temp, req.video_name)
        req.social_title = meta_temp.get("social_title", req.social_title)
        req.social_desc = meta_temp.get("social_desc", req.social_desc)
        req.social_tags = meta_temp.get("yt_tags", getattr(req, "social_tags", None))

        # Persistir en el JSON del video para que la tabla de Publicaciones tenga los metadatos limpios
        try:
            analysis_file_meta = get_analysis_file(req.video_name)
            if analysis_file_meta and os.path.exists(analysis_file_meta):
                with open(analysis_file_meta, "r", encoding="utf-8") as afm:
                    adata_m = json.load(afm)
                for lst_k in ("proposals", "completed_proposals"):
                    for c_item in adata_m.get(lst_k, []):
                        if c_item.get("id") in (req.clip_id, synced_clip_id):
                            if req.social_title:
                                c_item["social_title"] = req.social_title
                                c_item["yt_title"] = req.social_title
                            if req.social_desc:
                                c_item["social_desc"] = req.social_desc
                            if req.social_tags:
                                c_item["yt_tags"] = req.social_tags
                atomic_write_json(analysis_file_meta, adata_m)
        except Exception as e_m:
            print("Aviso guardando metadatos en export:", e_m)

        # Generar archivo _redes.txt en DB_DIR
        if synced_clip_id:
            txt_path = os.path.join(DB_DIR, f"{synced_clip_id}_redes.txt")
        elif getattr(req, "clip_id", None):
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
                    
        return {"status": "success", "output": out_file, "clip_id": synced_clip_id, "export_name": safe_name, "message": "Render iniciado en segundo plano."}
    except Exception as e:
        return {"status": "error", "message": str(e), "trace": traceback.format_exc()}

@app.post("/regenerate_metadata")
def regenerate_metadata(req: RegenerateMetadataRequest):
    try:
        from google import genai
        import pipeline, importlib
        importlib.reload(pipeline)
        from pipeline import extract_game_title, sanitize_and_format_metadata

        api_key = ""
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                api_key = json.load(f).get("gemini_api_key", "")
        if not api_key:
            raise Exception("No hay API Key configurada.")

        client = genai.Client(api_key=api_key.strip())
        game_title = extract_game_title(req.video_name)
        link_instruction = "que SIEMPRE termine la oración con 'Podes ver el video completo haciendo click en el link.' antes de los hashtags, " if "gourmet" in req.video_name.lower() else ""

        sys_prompt = (
            f"Sos Leito4Gaming, un streamer argentino jugando a {game_title}. "
            f"Escribí en español argentino natural y cotidiano (tratando de vos, en primera persona, como hablarías normalmente con amigos). "
            f"REGLAS ESTRICTAS:\n"
            f"1. CERO INSULTOS: Está PROHIBIDO poner malas palabras o insultos ('boludo', 'la puta madre', 'concha', 'mierda', 'carajo', 'cagazo', 'wtf', etc.) aunque estén en la transcripción.\n"
            f"2. CERO FRASES TONTAS O INFANTILES: No uses signos de exclamación exagerados ('¡Un bicho me quiso matar!') ni títulos todos en mayúsculas. Escribí de forma normal, sobria y auténtica contando qué pasó en el clip.\n"
            f"3. Devolvé ÚNICAMENTE un JSON válido con estos 3 campos:\n"
            f"- 'social_title': Título atractivo, natural y directo (sin insultos) que cuente qué pasa en el clip.\n"
            f"- 'social_desc': Descripción natural en primera persona (1 o 2 oraciones cortas, de 10 a 22 palabras, como hablarías vos normalmente) {link_instruction}seguida al final por 3 o 4 hashtags relevantes con '#' (incluyendo el del juego #{re.sub(r'[^a-zA-Z0-9]', '', game_title.title())} y #Leito4Gaming).\n"
            f"- 'yt_tags': String con 8 a 12 etiquetas para YouTube SEPARADAS POR COMA (sin '#'), que SIEMPRE incluya 'Leito4Gaming, {game_title}' y etiquetas específicas del juego y de la situación del clip."
        )

        response = client.models.generate_content(
            model='gemini-3.5-flash-lite',
            contents=[sys_prompt, f"JUEGO: {game_title}\nTRANSCRIPCIÓN DEL CLIP:\n{req.transcript}"],
            config={"temperature": 0.25, "response_mime_type": "application/json"}
        )
        txt = response.text
        match = re.search(r'\{.*\}', txt, re.DOTALL)
        if match:
            txt = match.group(0)
        else:
            txt = txt.replace('```json', '').replace('```', '').replace('`', '').strip()
        data = json.loads(txt)
        sanitize_and_format_metadata(data, req.video_name)
        return {
            "status": "success",
            "social_title": data.get("social_title", ""),
            "social_desc": data.get("social_desc", ""),
            "yt_tags": data.get("yt_tags", ""),
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

def align_words_to_voice_onset(wav_path: str, words_rel: list) -> list:
    """
    Ajusta los tiempos relativos [start, end] de cada palabra de Whisper al inicio acústico real (onset)
    de la voz en el archivo WAV de 16kHz, eliminando la anticipación de Whisper tras pausas o silencios.
    """
    if not words_rel or not os.path.exists(wav_path):
        return words_rel
    try:
        import wave
        import numpy as np

        with wave.open(wav_path, "rb") as wf:
            sr = wf.getframerate() or 16000
            raw = wf.readframes(wf.getnframes())
            samples = np.frombuffer(raw, dtype=np.int16).astype(np.float32)

        if len(samples) == 0:
            return words_rel

        hop = max(1, int(sr * 0.01))  # 10ms por frame (100 frames/seg)
        n_frames = len(samples) // hop
        if n_frames < 5:
            return words_rel

        frames = samples[:n_frames * hop].reshape(n_frames, hop)
        rms = np.sqrt(np.mean(frames ** 2, axis=1))
        kernel = np.array([0.25, 0.5, 0.25], dtype=np.float32)
        rms_smooth = np.convolve(rms, kernel, mode="same")

        global_p25 = float(np.percentile(rms_smooth, 25))
        global_p50 = float(np.percentile(rms_smooth, 50))

        aligned = []
        n_w = len(words_rel)

        for idx, w in enumerate(words_rel):
            w_copy = dict(w)
            txt = str(w_copy.get("word") or w_copy.get("text") or "").strip()
            clean_len = max(1, len(txt.strip(".,?!¡¿\"'()-")))
            ws = max(0.0, float(w_copy.get("start", 0.0)))
            we = max(ws + 0.06, float(w_copy.get("end", ws + 0.1)))

            if idx + 1 < n_w:
                next_s = float(words_rel[idx + 1].get("start", we))
                if next_s > ws + 0.04 and we > next_s:
                    we = next_s

            f_s = max(0, min(n_frames - 1, int(round(ws * 100))))
            f_e = max(f_s + 1, min(n_frames, int(round(we * 100))))

            ctx_s = max(0, f_s - 150)
            ctx_e = min(n_frames, f_e + 150)
            local_p25 = float(np.percentile(rms_smooth[ctx_s:ctx_e], 25))
            noise_floor = max(35.0, min(local_p25, global_p50 * 0.8, global_p25 * 1.6))

            seg_rms = rms_smooth[f_s:f_e]
            w_peak = float(np.max(seg_rms)) if len(seg_rms) > 0 else 0.0

            onset_thresh = max(noise_floor * 2.1, w_peak * 0.16, 120.0 if w_peak > 450 else w_peak * 0.30)

            dur = we - ws
            max_natural_dur = max(0.34, min(0.80, 0.16 + 0.058 * clean_len))

            if len(seg_rms) >= 4 and w_peak > noise_floor * 1.6:
                active_mask = seg_rms >= onset_thresh
                new_f_s = f_s
                new_f_e = f_e

                if np.any(active_mask):
                    runs = []
                    in_run = False
                    r_start = 0
                    for k, is_act in enumerate(active_mask):
                        if is_act and not in_run:
                            in_run = True
                            r_start = k
                        elif not is_act and in_run:
                            in_run = False
                            runs.append([r_start, k])
                    if in_run:
                        runs.append([r_start, len(active_mask)])

                    merged_runs = []
                    for r in runs:
                        if merged_runs and (r[0] - merged_runs[-1][1]) < 7:
                            merged_runs[-1][1] = r[1]
                        else:
                            merged_runs.append(r)

                    if len(merged_runs) == 1:
                        r0 = merged_runs[0]
                        new_f_s = f_s + r0[0]
                        if (len(seg_rms) - r0[1]) >= 20:
                            new_f_e = f_s + min(len(seg_rms), r0[1] + 5)
                    elif len(merged_runs) >= 2:
                        last_r = merged_runs[-1]
                        if last_r[1] >= len(seg_rms) - 1 and (last_r[1] - last_r[0]) <= 4 and (last_r[0] - merged_runs[-2][1]) >= 10:
                            merged_runs.pop()

                        if len(merged_runs) == 1:
                            r0 = merged_runs[0]
                            new_f_s = f_s + r0[0]
                            if (len(seg_rms) - r0[1]) >= 20:
                                new_f_e = f_s + min(len(seg_rms), r0[1] + 5)
                        elif dur > max(0.48, max_natural_dur * 1.15):
                            first_r = merged_runs[0]
                            last_r = merged_runs[-1]
                            e_first = float(np.sum(seg_rms[first_r[0]:first_r[1]]))
                            e_last = float(np.sum(seg_rms[last_r[0]:last_r[1]]))
                            gap_len = last_r[0] - first_r[1]
                            if first_r[0] <= 2 and (first_r[1] - first_r[0]) <= 14 and gap_len >= 12 and e_last >= e_first * 0.7:
                                new_f_s = f_s + last_r[0]
                                new_f_e = f_s + min(len(seg_rms), last_r[1] + 4)
                            elif e_first > e_last * 1.8 and gap_len >= 12:
                                new_f_s = f_s + first_r[0]
                                new_f_e = f_s + min(len(seg_rms), first_r[1] + 5)
                            else:
                                new_f_s = f_s + first_r[0]
                        else:
                            new_f_s = f_s + merged_runs[0][0]

                ws_snapped = new_f_s * 0.01
                we_snapped = max(ws_snapped + 0.08, new_f_e * 0.01)

                if (we_snapped - ws_snapped) > max_natural_dur * 1.4:
                    mid_f = int((new_f_s + new_f_e) // 2)
                    if new_f_s < mid_f < new_f_e:
                        h1_mean = float(np.mean(rms_smooth[new_f_s:mid_f]))
                        h2_mean = float(np.mean(rms_smooth[mid_f:new_f_e]))
                        if h1_mean < h2_mean * 0.38:
                            ws_snapped = max(ws_snapped, we_snapped - max_natural_dur)

                ws = ws_snapped
                we = we_snapped
            elif dur > max_natural_dur:
                ws = max(ws, we - max_natural_dur)

            # Ajuste perceptual de +20ms para que el subtítulo aparezca exacto con el golpe de voz y nunca antes
            if (we - ws) >= 0.14:
                ws = min(we - 0.08, ws + 0.02)

            w_copy["start"] = round(ws, 2)
            w_copy["end"] = round(max(we, ws + 0.08), 2)
            aligned.append(w_copy)

        for i in range(len(aligned) - 1):
            if aligned[i]["end"] > aligned[i + 1]["start"]:
                aligned[i]["end"] = round(max(aligned[i]["start"] + 0.05, aligned[i + 1]["start"]), 2)

        return aligned
    except Exception as e_al:
        print(f"Aviso en align_words_to_voice_onset: {e_al}")
        return words_rel


@app.post("/transcribe")
def transcribe_audio(req: TranscribeRequest):
    try:
        import subprocess
        import whisper
        import torch
        from pipeline import extract_game_title

        video_path = find_video_path(req.video_name)
        if not os.path.exists(video_path):
            return {"status": "error", "message": "Video no encontrado."}

        temp_audio = os.path.join(TEMP_CLIPS_DIR, f"{req.clip_id}_audio.wav")
        # Filtro vocal sin lookahead (sin dynaudnorm) para mantener latencia cero y contraste real silencio/voz
        audio_filter = "highpass=f=85,lowpass=f=7800"
        cmd = [
            FFMPEG_BIN, "-y", "-accurate_seek", "-ss", str(req.start), "-t", str(req.end - req.start),
            "-i", video_path, "-map", f"0:a:{req.track - 1}",
            "-vn", "-af", audio_filter,
            "-acodec", "pcm_s16le", "-ar", "16000", "-ac", "1", temp_audio
        ]
        try:
            subprocess.run(cmd, check=True, capture_output=True)
        except subprocess.CalledProcessError as e:
            if req.track > 1:
                print(f"Advertencia: No se encontró la Pista {req.track}. Cayendo de vuelta a la Pista 1 (0:a:0).")
                cmd[cmd.index("-map") + 1] = "0:a:0"
                subprocess.run(cmd, check=True, capture_output=True)
            else:
                raise Exception(f"FFmpeg error: {e.stderr.decode('utf-8', errors='ignore')}")

        game_title = extract_game_title(req.video_name)
        device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"Cargando modelo Whisper en {device} para transcribir clip de {game_title}...")
        whisper_model = whisper.load_model("small", device=device)

        clean_prompt = (
            f"Gameplay en español argentino de {game_title}. "
            f"Mirá, fijate acá, cuidado, corre, no puede ser, qué pasó, boludo, hermano, amigo, dale."
        )
        result = whisper_model.transcribe(
            temp_audio,
            word_timestamps=True,
            language="es",
            initial_prompt=clean_prompt,
            condition_on_previous_text=False,
            beam_size=5,
            best_of=5,
            temperature=(0.0, 0.2, 0.4),
            no_speech_threshold=0.6,
            logprob_threshold=-1.0,
        )

        words_rel = []
        for seg in result.get("segments", []):
            if seg.get("no_speech_prob", 0.0) > 0.82:
                continue
            for w in seg.get("words", []):
                w_txt = str(w.get("word", "")).strip()
                if not w_txt:
                    continue
                prob = float(w.get("probability", 1.0) or 1.0)
                w_s = float(w.get("start", 0.0))
                w_e = float(w.get("end", w_s + 0.1))
                # Filtrar alucinaciones de ruido muy improbables de 1-2 letras
                if prob < 0.14 and len(w_txt.strip(".,?!¡¿")) <= 2:
                    continue
                words_rel.append({
                    "word": w_txt,
                    "start": max(0.0, w_s),
                    "end": max(w_e, w_s + 0.06),
                })

        if device == "cuda":
            del whisper_model
            torch.cuda.empty_cache()

        # Paso 1.5: Alinear cada palabra al onset acústico real de la voz (elimina anticipación de Whisper tras pausas)
        words_rel = align_words_to_voice_onset(temp_audio, words_rel)

        words_out = [
            {
                "word": w["word"],
                "start": round(req.start + w["start"], 2),
                "end": round(req.start + max(w["end"], w["start"] + 0.08), 2),
            }
            for w in words_rel
        ]

        # Paso 2: Corrección fonética asistida por Gemini Flash-Lite escuchando el audio real
        # (Mantiene INTACTOS los tiempos start/end de cada palabra de Whisper y solo corrige palabras mal entendidas o borra ruidos falsos)
        api_key = ""
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as cf:
                    api_key = json.load(cf).get("gemini_api_key", "").strip()
            except Exception:
                api_key = ""

        if api_key and len(words_out) > 0:
            temp_mp3 = os.path.join(TEMP_CLIPS_DIR, f"{req.clip_id}_verify.mp3")
            try:
                from google import genai
                from google.genai import types
                subprocess.run([
                    FFMPEG_BIN, "-y", "-i", temp_audio,
                    "-ac", "1", "-ar", "16000", "-c:a", "libmp3lame", "-b:a", "48k",
                    temp_mp3
                ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

                with open(temp_mp3, "rb") as f_mp3:
                    aud_part = types.Part.from_bytes(data=f_mp3.read(), mime_type="audio/mp3")

                indexed_words = " | ".join(f"{idx}:{w['word']}" for idx, w in enumerate(words_out))
                fix_prompt = (
                    f"Sos un corrector experto de subtítulos en español argentino para un gameplay de '{game_title}'.\n"
                    f"Escuchá el audio adjunto y revisá esta lista de palabras numeradas que transcribió Whisper:\n"
                    f"{indexed_words}\n\n"
                    f"REGLAS ESTRICTAS:\n"
                    f"1. CADA ÍNDICE TIENE UN TIEMPO FIJO EN LA LÍNEA DE TIEMPO. PROHIBIDO correr palabras de un índice a otro.\n"
                    f"2. Si una palabra en el índice 'i' fue mal entendida fonéticamente por Whisper (ej: puso 'bolita' en vez de 'boleta', 'apuertado' en vez de 'apretado', 'niza' en vez de nada, o escribió mal un término en español/inglés), devolvé su corrección exacta para ese mismo índice 'i'.\n"
                    f"3. Si en un índice 'i' Whisper inventó una palabra donde solo había un grito puro ('aaah'), respiración, risa o ruido del juego sin palabra hablada, poné 'w': '' (vacío) en ese índice 'i' para eliminar esa alucinación.\n"
                    f"4. Devolvé ÚNICAMENTE este JSON: {{\"fixes\": [{{\"i\": int, \"w\": \"palabra_corregida_o_vacio\"}}]}} (si todas están bien, devolvé {{\"fixes\": []}})."
                )
                client = genai.Client(api_key=api_key, http_options={'timeout': 45000})
                resp = client.models.generate_content(
                    model="gemini-3.5-flash-lite",
                    contents=[aud_part, fix_prompt],
                    config={"temperature": 0.1, "response_mime_type": "application/json"},
                )
                m = re.search(r"\{.*\}", resp.text or "", re.DOTALL)
                if m:
                    fix_data = json.loads(m.group(0))
                    to_delete = set()
                    fixes_list = fix_data.get("fixes", [])
                    if isinstance(fixes_list, list):
                        for fx in fixes_list:
                            if not isinstance(fx, dict) or "i" not in fx:
                                continue
                            idx_f = int(fx["i"])
                            if 0 <= idx_f < len(words_out):
                                new_w = str(fx.get("w", "")).strip()
                                if new_w == "":
                                    to_delete.add(idx_f)
                                else:
                                    words_out[idx_f]["word"] = new_w
                    if to_delete:
                        words_out = [w for idx_w, w in enumerate(words_out) if idx_w not in to_delete]
                    print(f"Subtítulos verificados con audio por IA: {len(fixes_list)} correcciones aplicadas.")
            except Exception as e_fix:
                print(f"Aviso en verificación de subtítulos con IA (usando Whisper directo): {e_fix}")
            finally:
                try:
                    if os.path.exists(temp_mp3):
                        os.remove(temp_mp3)
                except Exception:
                    pass

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
            atomic_write_json(analysis_file, data)
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
                
        atomic_write_json(analysis_file, data)
            
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
            atomic_write_json(filepath, data)
                
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
        
        out_path = os.path.join(temp_dir, f'audio_track_{track_index}_{start}_{end}.wav')
        
        if not os.path.exists(out_path):
            # Agregar 6s extra en pista de voz por si el usuario adelanta el audio (desfase negativo) en el monitoreo en vivo
            extra_pad = 6.0 if int(track_index) == 1 else 0.5
            dur_track = max(0.1, float(end) - float(start) + extra_pad)
            cmd = [
                FFMPEG_BIN, '-y', '-hide_banner', '-loglevel', 'error',
                '-accurate_seek', '-ss', str(start), '-t', str(dur_track),
                '-i', video_path,
                '-vn', '-map', f'0:a:{track_index}',
                '-c:a', 'pcm_s16le',
                out_path
            ]
            try:
                subprocess.run(cmd, check=True)
            except subprocess.CalledProcessError:
                cmd[cmd.index('-map') + 1] = '0:a:0'
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
                "-filter_complex", f"[0:a:{tv}]volume={req.vol_voz}[a1];[0:a:{tj}]volume={req.vol_juego}[a2];[a1][a2]amix=inputs=2:duration=first:dropout_transition=0,volume=2[a]",
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


