import re

with open(r'c:\Users\leone\Desktop\OBS Grabaciones\Exports\Complete Games\templates\index.html', 'r', encoding='utf-8') as f:
    html = f.read()

audio_panel_html = '''
            <div id="panel-audio" style="display:none;">
                <div style="color: var(--accent-primary); font-weight: 600; margin-bottom: 15px; font-size: 14px; text-transform: uppercase; letter-spacing: 1px;">Mezclador de Audio</div>
                
                <div class="setting-group">
                    <label>Volumen de tu Voz (Microfono)</label>
                    <div style="display:flex; align-items:center; gap:10px;">
                        <input type="range" id="vol-voz" min="0" max="2" step="0.1" value="1.0" style="flex:1;">
                        <span id="lbl-vol-voz" style="width:30px; font-size:12px; text-align:right;">1.0</span>
                    </div>
                </div>

                <div class="setting-group">
                    <label>Volumen del Juego</label>
                    <div style="display:flex; align-items:center; gap:10px;">
                        <input type="range" id="vol-juego" min="0" max="2" step="0.1" value="1.0" style="flex:1;">
                        <span id="lbl-vol-juego" style="width:30px; font-size:12px; text-align:right;">1.0</span>
                    </div>
                </div>

                <button class="btn" style="background: var(--bg-hover); width:100%; margin-top:10px;" onclick="generateAudioPreview()">Generar Previsualizacion</button>
                
                <div id="audio-preview-container" style="display:none; margin-top:15px; padding:10px; background:#111; border-radius:8px;">
                    <audio id="audio-preview-player" controls style="width:100%; height:30px;"></audio>
                </div>
            </div>
'''

if 'id="panel-audio"' not in html:
    html = html.replace('<div id="panel-final" style="display:none;">', audio_panel_html + '\n<div id="panel-final" style="display:none;">')

with open(r'c:\Users\leone\Desktop\OBS Grabaciones\Exports\Complete Games\templates\index.html', 'w', encoding='utf-8') as f:
    f.write(html)
