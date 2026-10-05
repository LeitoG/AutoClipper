with open('backend.py', 'r', encoding='utf-8') as f:
    text = f.read()

target = '''@app.post("/generate_clips")
def generate_clips(req: GenerateClipsRequest):
    try:
        import time'''

replacement = '''def _generate_clips_task(req: GenerateClipsRequest):
    try:
        import time'''

text = text.replace(target, replacement)

target2 = '''@app.post("/generate_clips")
def _generate_clips_task'''

# Since we replaced the def, we need to add the endpoint back above it
target3 = '''def _generate_clips_task(req: GenerateClipsRequest):'''
replacement3 = '''@app.post("/generate_clips")
def generate_clips(req: GenerateClipsRequest, background_tasks: BackgroundTasks):
    if analysis_progress.get("status") == "processing":
        return {"status": "error", "message": "Ya hay un proceso de generaci\u00f3n en curso. Espera a que termine."}
    
    background_tasks.add_task(_generate_clips_task, req)
    return {"status": "success", "message": "Generaci\u00f3n iniciada en segundo plano."}

def _generate_clips_task(req: GenerateClipsRequest):'''

text = text.replace(target3, replacement3)

with open('backend.py', 'w', encoding='utf-8') as f:
    f.write(text)
print("generate_clips extracted to background task")
