import sys
import os
import datetime
import subprocess

# --- CONFIGURACION ---
MOSTRAR_NOTIFICACION_VISUAL = True  # Cambia a False si no quieres ver el cartelito silencioso
# ---------------------

now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
hora_corta = datetime.datetime.now().strftime('%H:%M:%S')

# Guardar en ambas rutas de base de datos para asegurar sincronización total con el backend
db_dirs = [
    os.path.join(os.path.dirname(os.path.abspath(__file__)), 'db'),
    r"C:\Users\leone\Desktop\OBS Grabaciones\Exports\Complete Games\db"
]

saved_paths = set()
for d in db_dirs:
    try:
        norm_d = os.path.normcase(os.path.abspath(d))
        if norm_d in saved_paths:
            continue
        saved_paths.add(norm_d)
        os.makedirs(d, exist_ok=True)
        markers_file = os.path.join(d, 'markers.txt')
        with open(markers_file, 'a', encoding='utf-8') as f:
            f.write(f"{now}\n")
    except Exception as e:
        print(f"Error guardando en {d}: {e}")

print(f"Marcador guardado (SIN SONIDO) a las {now}")

# Feedback Visual 100% Silencioso (Toast flotante sin robar foco del juego y sin sonido de Windows)
if MOSTRAR_NOTIFICACION_VISUAL:
    ps_script = f"""
    Add-Type -AssemblyName System.Windows.Forms
    Add-Type -AssemblyName System.Drawing
    $form = New-Object System.Windows.Forms.Form
    $form.FormBorderStyle = [System.Windows.Forms.FormBorderStyle]::None
    $form.StartPosition = [System.Windows.Forms.FormStartPosition]::Manual
    $form.Size = New-Object System.Drawing.Size(260, 48)
    $screen = [System.Windows.Forms.Screen]::PrimaryScreen.WorkingArea
    $form.Location = New-Object System.Drawing.Point(($screen.Right - 280), ($screen.Bottom - 68))
    $form.BackColor = [System.Drawing.Color]::FromArgb(24, 24, 36)
    $form.TopMost = $true
    $form.ShowInTaskbar = $false
    $form.Opacity = 0.92

    $lbl = New-Object System.Windows.Forms.Label
    $lbl.Text = "📌 Clip marcado ({hora_corta})"
    $lbl.ForeColor = [System.Drawing.Color]::FromArgb(16, 185, 129)
    $lbl.Font = New-Object System.Drawing.Font("Segoe UI", 11, [System.Drawing.FontStyle]::Bold)
    $lbl.AutoSize = $false
    $lbl.Size = $form.Size
    $lbl.TextAlign = [System.Drawing.ContentAlignment]::MiddleCenter
    $form.Controls.Add($lbl)

    $timer = New-Object System.Windows.Forms.Timer
    $timer.Interval = 2000
    $timer.Add_Tick({{
        $timer.Stop()
        $form.Close()
    }})
    $form.Add_Shown({{ $timer.Start() }})
    [System.Windows.Forms.Application]::Run($form)
    """
    try:
        subprocess.Popen(
            ["powershell", "-NoProfile", "-WindowStyle", "Hidden", "-Command", ps_script],
            creationflags=subprocess.CREATE_NO_WINDOW
        )
    except Exception as e:
        print("Error enviando notificacion visual silenciosa:", e)
