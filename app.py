import webview
import threading
import uvicorn
import time

from backend import app

def start_server():
    uvicorn.run(app, host='127.0.0.1', port=8000, log_level='error')

if __name__ == '__main__':
    # Arrancar el backend de FastAPI en un hilo de fondo
    server_thread = threading.Thread(target=start_server, daemon=True)
    server_thread.start()
    
    # Random timestamp to DESTROY WebView2 cache
    timestamp = int(time.time())

    # Crear y mostrar la ventana de la aplicacion
    webview.create_window(
        'AutoClipper 2.0',
        f'http://127.0.0.1:8000/?t={timestamp}',
        width=1280,
        height=800,
        min_size=(1024, 768),
        background_color='#0f172a'
    )
    
    # Iniciar (usamos el perfil default por ahora)
    webview.start(private_mode=False)