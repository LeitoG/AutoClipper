with open('backend.py', 'r', encoding='utf-8') as f:
    text = f.read()

target = '''        return {"status": "success", "message": "Generaci\u00f3n iniciada en segundo plano."}

def _generate_clips_task(req: GenerateClipsRequest):
    try:'''

replacement = '''        return {"status": "success", "message": "Generaci\u00f3n iniciada en segundo plano."}

def _generate_clips_task(req: GenerateClipsRequest):
    try:
        analysis_progress["status"] = "processing"
        analysis_progress["percent"] = 0
        analysis_progress["message"] = "Inicializando entorno de IA..."'''

text = text.replace(target, replacement)


# Replace return {"status": "error"} inside the task with setting analysis_progress
target2 = '''        video_file_name = req.video_name
        if not video_file_name:
            return {"status": "error", "message": "No hay video activo."}'''
replacement2 = '''        video_file_name = req.video_name
        if not video_file_name:
            analysis_progress["status"] = "error"
            analysis_progress["message"] = "No hay video activo."
            return'''
text = text.replace(target2, replacement2)

target3 = '''        video_path = find_video_path(video_file_name)
        if not os.path.exists(video_path):
            return {"status": "error", "message": f"Video no encontrado: {video_path}"}'''
replacement3 = '''        video_path = find_video_path(video_file_name)
        if not os.path.exists(video_path):
            analysis_progress["status"] = "error"
            analysis_progress["message"] = f"Video no encontrado: {video_path}"
            return'''
text = text.replace(target3, replacement3)

target4 = '''        if not gemini_api_key:
            return {"status": "error", "message": "No se ha configurado la API Key de Gemini en los ajustes."}'''
replacement4 = '''        if not gemini_api_key:
            analysis_progress["status"] = "error"
            analysis_progress["message"] = "No se ha configurado la API Key de Gemini en los ajustes."
            return'''
text = text.replace(target4, replacement4)

target5 = '''        except ImportError:
            return {"status": "error", "message": "Falta el archivo pipeline.py."}'''
replacement5 = '''        except ImportError:
            analysis_progress["status"] = "error"
            analysis_progress["message"] = "Falta el archivo pipeline.py."
            return'''
text = text.replace(target5, replacement5)

target6 = '''        if current_month not in costs_data:
            costs_data[current_month] = {"tokens": 0, "cost": 0.0}
        costs_data[current_month]["tokens"] += total_in + total_out
        
        # Calculate cost
        in_cost = (total_in / 1_000_000) * 0.075
        out_cost = (total_out / 1_000_000) * 0.30
        costs_data[current_month]["cost"] += in_cost + out_cost
        
        with open(COSTS_FILE, "w", encoding="utf-8") as f:
            json.dump(costs_data, f, indent=4)
            
        return {"status": "success", "new_clips": len(all_new_clips)}
        
    except Exception as e:
        return {"status": "error", "message": str(e)}'''

replacement6 = '''        if current_month not in costs_data:
            costs_data[current_month] = {"tokens": 0, "cost": 0.0}
        costs_data[current_month]["tokens"] += total_in + total_out
        
        # Calculate cost
        in_cost = (total_in / 1_000_000) * 0.075
        out_cost = (total_out / 1_000_000) * 0.30
        costs_data[current_month]["cost"] += in_cost + out_cost
        
        with open(COSTS_FILE, "w", encoding="utf-8") as f:
            json.dump(costs_data, f, indent=4)
            
    except Exception as e:
        analysis_progress["status"] = "error"
        analysis_progress["message"] = str(e)'''

text = text.replace(target6, replacement6)

with open('backend.py', 'w', encoding='utf-8') as f:
    f.write(text)
print("generate_clips error handling refactored")
