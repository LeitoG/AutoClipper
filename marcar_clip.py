import sys
import os
import datetime
import winsound
import subprocess

# --- CONFIGURACION ---
MOSTRAR_NOTIFICACION_VISUAL = True  # Cambia a False si no quieres ver el cartelito
# ---------------------

db_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'db')
os.makedirs(db_dir, exist_ok=True)
markers_file = os.path.join(db_dir, 'markers.txt')

now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

with open(markers_file, 'a', encoding='utf-8') as f:
    f.write(f"{now}\n")

print(f"Marcador guardado a las {now}")

# Feedback de Sonido
try:
    winsound.PlaySound("SystemAsterisk", winsound.SND_ALIAS | winsound.SND_ASYNC)
except:
    pass

# Feedback Visual (Notificacion de Windows)
if MOSTRAR_NOTIFICACION_VISUAL:
    ps_script = """
    [reflection.assembly]::loadwithpartialname('System.Windows.Forms') | Out-Null
    [reflection.assembly]::loadwithpartialname('System.Drawing') | Out-Null
    $notify = New-Object System.Windows.Forms.NotifyIcon
    $notify.Icon = [System.Drawing.SystemIcons]::Information
    $notify.Visible = $true
    $notify.ShowBalloonTip(3000, 'AutoClipper', '¡Clip marcado con exito a las ' + (Get-Date -Format 'HH:mm:ss') + '!', [System.Windows.Forms.ToolTipIcon]::Info)
    Start-Sleep -s 3
    $notify.Dispose()
    """
    try:
        subprocess.Popen(["powershell", "-WindowStyle", "Hidden", "-Command", ps_script], creationflags=subprocess.CREATE_NO_WINDOW)
    except Exception as e:
        print("Error enviando notificacion:", e)
