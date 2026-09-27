import subprocess

FFMPEG_BIN = r'C:\Users\leone\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1.1-full_build\bin\ffmpeg.exe'
video_path = r'D:\OBS Grabaciones Secondary Disk\OBS Videos\The Closing Shift\Test\2026-06-14_21-09-06.mkv'
out_file = r'C:/Users/leone/Desktop/OBS Grabaciones/Exports/Clips_AI/test_render.mp4'

ass_path = r'C:/Users/leone/Desktop/OBS Grabaciones/Exports/Clips_AI/subs_test_auto.ass'
ass_ff = ass_path.replace('\\', '/').replace(':', '\\:')

filter_complex = f"[0:v]crop=324:576:1088:0[face_c]; [face_c]scale=1080:1920[face_s]; [0:v]crop=1920:1080:0:0[game_c]; [game_c]scale=1080:607[game_s]; color=c=black:s=1080x1920[bg]; [bg][face_s]overlay=0:0[bg1]; [bg1][game_s]overlay=0:1313[v_game]; [v_game]subtitles='{ass_ff}'[v]"

cmd = [FFMPEG_BIN, '-y', '-ss', '0', '-t', '1', '-i', video_path, '-filter_complex', filter_complex, '-map', '[v]', '-map', '0:a', '-c:v', 'libx264', '-preset', 'ultrafast', '-crf', '23', '-c:a', 'aac', out_file]

with open("ffmpeg_error.log", "w") as f:
    subprocess.run(cmd, stderr=f, stdout=f)
