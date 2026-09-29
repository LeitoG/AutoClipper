import json
with open('backend.py', 'r', encoding='utf-8') as f:
    text = f.read()

req_class = '''class RegenerateMetadataRequest(BaseModel):
    video_name: str
    transcript: str

'''

endpoint = '''@app.post("/regenerate_metadata")
def regenerate_metadata(req: RegenerateMetadataRequest):
    try:
        from google import genai
        config_data = load_config()
        api_key = config_data.get("gemini_api_key", "")
        if not api_key:
            raise Exception("No hay API Key configurada.")
        
        client = genai.Client(api_key=api_key.strip())
        
        link_instruction = "que SIEMPRE termine con 'Podes ver el video completo haciendo click en el link' seguida de los " if "gourmet" in req.video_name.lower() else ""
        
        sys_prompt = f"Eres Leito4Gaming, un streamer y creador de videos virales de gaming de Argentina. Escribe en Espanol Argentino autentico (rioplatense), NUNCA uses 'tu', habla de VOS. Escribe en PRIMERA PERSONA. Recibes la transcripcion de un clip de tu video ({req.video_name}). Tu tarea es generar UNICAMENTE un JSON valido con dos campos: 'social_title' (string, Titulo ingenioso y directo que resuma EXACTAMENTE lo que pasa o se dice en el clip) y 'social_desc' (string, descripcion MUY CORTA de APENAS UN RENGLON (maximo 10 palabras) que tenga sentido con el clip, en PRIMERA PERSONA. {link_instruction} Luego pon solo 3 hashtags populares del juego). NO uses markdown, solo el JSON raw."
        
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=[sys_prompt, f"TRANSCRIPCION:\\n{req.transcript}"]
        )
        txt = response.text.replace('`json', '').replace('`', '').strip()
        data = json.loads(txt)
        return {"status": "success", "social_title": data.get("social_title", ""), "social_desc": data.get("social_desc", "")}
    except Exception as e:
        return {"status": "error", "message": str(e)}

'''

text = text.replace('class TranscribeRequest(BaseModel):', req_class + 'class TranscribeRequest(BaseModel):')
text = text.replace('@app.post("/transcribe")', endpoint + '@app.post("/transcribe")')

with open('backend.py', 'w', encoding='utf-8') as f:
    f.write(text)
print("Added Regenerate endpoint")
