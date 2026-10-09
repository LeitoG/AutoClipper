with open('pipeline.py', 'r', encoding='utf-8') as f:
    text = f.read()
idx = text.find('is_excluded = True', text.find('def analyze_video_semantic'))
idx = text.find('is_excluded = True', idx+1)
if idx != -1:
    print(text[idx:idx+1500])
