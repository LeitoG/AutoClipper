import os
import json

db_dir = r'C:\Users\leone\Desktop\OBS Grabaciones\Exports\Complete Games\db'
for f in os.listdir(db_dir):
    if f.endswith('.json'):
        path = os.path.join(db_dir, f)
        try:
            with open(path, 'r', encoding='utf-8') as file:
                json.load(file)
        except Exception as e:
            print(f"Corrupted file: {f} - {e}")
