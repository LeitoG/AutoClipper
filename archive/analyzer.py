import os
import json
import whisper
import numpy as np
import cv2
import mediapipe as mp
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision as mp_vision
import urllib.request
from moviepy import AudioFileClip
import argparse

OUTPUT_DIR = r"C:\Users\leone\Desktop\OBS Grabaciones\Exports\Clips_AI"

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
        new_w = min(1920, int(w * 4.0)) # Ampliar cuadro
        new_h = min(1080, int(h * 4.0))
        new_x = max(0, cx - new_w//2)
        new_y = max(0, cy - new_h//2)
        
        if new_x + new_w > 1920: new_x = 1920 - new_w
        if new_y + new_h > 1080: new_y = 1080 - new_h
        
        return new_x, new_y, new_w, new_h
    return 1500, 600, 420, 480 # Fallback

def get_loudest_moments(audio_clip, num_moments=3):
    print("Analizando picos de volumen en el audio...")
    chunk_size = 5.0
    duration = int(audio_clip.duration)
    moments = []
    
    for t in range(0, duration, int(chunk_size)):
        try:
            sub = audio_clip.subclipped(t, min(t + chunk_size, duration))
            arr = sub.to_soundarray(fps=11025) 
            rms = np.sqrt(np.mean(arr**2))
            moments.append((t, rms))
        except Exception:
            pass
            
    # Sort by RMS descending
    moments.sort(key=lambda x: x[1], reverse=True)
    
    # Filter out overlapping moments
    best_moments = []
    for t, rms in moments:
        if not any(abs(t - bt) < 60 for bt, _ in best_moments):
            best_moments.append((t, rms))
        if len(best_moments) >= num_moments:
            break
            
    return best_moments

def analyze_video(video_path):
    print(f"Analizando video: {video_path}")
    basename = os.path.basename(video_path)
    
    # 1. Facecam Tracking
    face_x, face_y, face_w, face_h = get_dynamic_facecam_crop(video_path)
    
    # 2. Volume Analysis
    print("Cargando AudioFileClip...")
    audio_clip = AudioFileClip(video_path)
    loudest_moments = get_loudest_moments(audio_clip)
    audio_clip.close()
    
    # 3. Whisper Transcription (we use small model to speed up testing)
    print("Transcribiendo video con Whisper...")
    model = whisper.load_model("small")
    result = model.transcribe(video_path, word_timestamps=True)
    
    # 4. Generate Clip JSON proposals
    clip_proposals = []
    
    for idx, (peak_t, rms) in enumerate(loudest_moments):
        # Queremos duracion de entre 35s y 59s. Haremos 50s.
        # El susto o hype ocurre en peak_t. Pondremos peak_t en el segundo 35 para dar contexto antes.
        start_t = max(0, peak_t - 35)
        end_t = min(int(audio_clip.duration), start_t + 50)
        
        # Encontrar texto
        segment_texts = []
        for s in result["segments"]:
            if s["start"] >= start_t and s["end"] <= end_t:
                segment_texts.append(s["text"])
        
        clip_text = " ".join(segment_texts)
        if not clip_text:
            clip_text = "Moment of tension / action"
            
        proposal = {
            "id": f"clip_{idx+1}",
            "start": start_t,
            "end": end_t,
            "duration": end_t - start_t,
            "reason": f"Pico de volumen alto detectado (RMS: {rms:.4f})",
            "context": clip_text[:150] + "...",
            "suggested_template": "Template A (Split 50/50 Facecam/Gameplay)",
            "facecam_coords": {"x": face_x, "y": face_y, "w": face_w, "h": face_h}
        }
        clip_proposals.append(proposal)
        
    output_json = {
        "video": basename,
        "proposals": clip_proposals,
        "full_transcription_path": "MEMORIA"
    }
    
    with open("analysis.json", "w", encoding="utf-8") as f:
        json.dump(output_json, f, indent=4, ensure_ascii=False)
        
    print("===ANTIGRAVITY_JSON_READY===")
    
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', type=str, required=True)
    args = parser.parse_args()
    analyze_video(args.input)
