import webview
import threading
import uvicorn
import random

from backend import app

PORT = random.randint(8100, 8900)

def start_server():
    uvicorn.run(app, host='127.0.0.1', port=PORT, log_level='info')

if __name__ == '__main__':
    server_thread = threading.Thread(target=start_server, daemon=True)
    server_thread.start()
    
    webview.create_window(
        'AutoClipper 2.0',
        f'http://127.0.0.1:{PORT}',
        width=1280,
        height=800,
        min_size=(1024, 768),
        background_color='#0f172a'
    )
    
    webview.start(private_mode=True)
