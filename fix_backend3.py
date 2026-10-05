with open('backend.py', 'r', encoding='utf-8') as f:
    text = f.read()

target = '''@app.post("/generate_clips")
def generate_clips(req: GenerateClipsRequest, background_tasks: BackgroundTasks):
    if analysis_progress.get("status") == "processing":
        return {"status": "error", "message": "Ya hay un proceso de generaci\u00f3n en curso. Espera a que termine."}
    
    background_tasks.add_task(_generate_clips_task, req)
    return {"status": "success", "message": "Generaci\u00f3n iniciada en segundo plano."}

def _generate_clips_task(req: GenerateClipsRequest):
    try:
        analysis_progress["status"] = "processing"
        analysis_progress["percent"] = 0
        analysis_progress["message"] = "Inicializando entorno de IA..."'''

replacement = '''@app.post("/generate_clips")
def generate_clips(req: GenerateClipsRequest, background_tasks: BackgroundTasks):
    if analysis_progress.get("status") == "processing":
        return {"status": "error", "message": "Ya hay un proceso de generaci\u00f3n en curso. Espera a que termine."}
    
    analysis_progress["status"] = "processing"
    analysis_progress["percent"] = 0
    analysis_progress["message"] = "Inicializando entorno de IA..."
    background_tasks.add_task(_generate_clips_task, req)
    return {"status": "success", "message": "Generaci\u00f3n iniciada en segundo plano."}

def _generate_clips_task(req: GenerateClipsRequest):
    try:'''

text = text.replace(target, replacement)

with open('backend.py', 'w', encoding='utf-8') as f:
    f.write(text)
print("status sync fixed")
