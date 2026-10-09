import sys
import os
import datetime

db_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'db')
os.makedirs(db_dir, exist_ok=True)
markers_file = os.path.join(db_dir, 'markers.txt')

now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

with open(markers_file, 'a', encoding='utf-8') as f:
    f.write(f"{now}\n")

print(f"Marcador guardado a las {now}")
