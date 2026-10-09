import re

with open('backend.py', 'r', encoding='utf-8') as f:
    text = f.read()

target = r"analyze_video_semantic\(\s*video_path, req\.prompt, gemini_api_key, TEMP_CLIPS_DIR, prog_sem, exclusion_zones,\s*incremental_save, req\.max_clips\s*\)"

replacement = r'''analyze_video_semantic(
                video_path, req.prompt, gemini_api_key, TEMP_CLIPS_DIR, prog_sem, exclusion_zones, 
                incremental_save, req.max_clips, req.keywords
            )'''

new_text = re.sub(target, replacement, text, flags=re.DOTALL)
if new_text != text:
    with open('backend.py', 'w', encoding='utf-8') as f:
        f.write(new_text)
    print("Replaced!")
else:
    print("Not replaced.")
