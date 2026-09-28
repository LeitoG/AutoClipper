import webview
import threading
import uvicorn
import time

from backend import app

def start_server():
    uvicorn.run(app, host='127.0.0.1', port=8000, log_level='info')

if __name__ == '__main__':
    server_thread = threading.Thread(target=start_server, daemon=True)
    server_thread.start()
    
    timestamp = int(time.time())
    webview.create_window(
        'AutoClipper 2.0',
        f'http://127.0.0.1:8000/?t={timestamp}',
        width=1280,
        height=800,
        min_size=(1024, 768),
        background_color='#0f172a'
    )
    
    import os
    app_data_dir = os.path.join(os.environ.get('APPDATA', '.'), 'AutoClipper')
    os.makedirs(app_data_dir, exist_ok=True)
    webview.start(private_mode=False, storage_path=app_data_dir)
