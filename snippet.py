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
