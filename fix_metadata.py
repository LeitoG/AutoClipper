with open('backend.py', 'r', encoding='utf-8') as f:
    text = f.read()

target = '''    try:
        from google import genai
        config_data = load_config()
        api_key = config_data.get("gemini_api_key", "")'''

replacement = '''    try:
        from google import genai
        api_key = ""
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                api_key = json.load(f).get("gemini_api_key", "")'''

text = text.replace(target, replacement)

with open('backend.py', 'w', encoding='utf-8') as f:
    f.write(text)
print("Fixed regenerate_metadata")
