import re

with open('pipeline.py', 'r', encoding='utf-8') as f:
    text = f.read()

target = r"        # Cortar audio del chunk.*?chunk_mp3_path\s*\]\s*, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL\)"

replacement = r'''        # Cortar audio y video (low fps) del chunk para contexto visual completo
        chunk_mp3_path = os.path.join(temp_dir, f"chunk_{chunk_idx}.mp4")
        subprocess.run([
            "ffmpeg", "-y", "-ss", str(chunk_start), "-to", str(chunk_end),
            "-skip_frame", "nokey", "-i", video_path, 
            "-vf", "scale=480:-2,fps=1", "-c:v", "libx264", "-preset", "ultrafast", "-crf", "35",
            "-c:a", "libmp3lame", "-q:a", "5",
            chunk_mp3_path
        ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)'''

new_text = re.sub(target, replacement, text, flags=re.DOTALL)
if new_text != text:
    with open('pipeline.py', 'w', encoding='utf-8') as f:
        f.write(new_text)
    print("Replaced chunk extraction!")
else:
    print("Not replaced.")
