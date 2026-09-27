import webview
import threading
import uvicorn
import os
from backend import app

def start_server():
    uvicorn.run(app, host='127.0.0.1', port=8000, log_level='error')

if __name__ == '__main__':
    # Arrancar el backend de FastAPI en un hilo de fondo
    server_thread = threading.Thread(target=start_server, daemon=True)
    server_thread.start()

    # Crear y mostrar la ventana de la aplicacion
    webview.create_window(
        'AutoClipper 2.0',
        'http://127.0.0.1:8000',
        width=1280,
        height=800,
        min_size=(1024, 768),
        background_color='#0f172a'
    )
    # private_mode=True disables caching and persistent cookies completely!
    webview.start(private_mode=True)
