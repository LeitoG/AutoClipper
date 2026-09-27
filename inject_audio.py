import re

with open(r'c:\Users\leone\Desktop\OBS Grabaciones\Exports\Complete Games\templates\index.html', 'r', encoding='utf-8') as f:
    html = f.read()

audio_panel_html = '''
            <!-- PESTAÑA: AUDIO -->
            <div id="panel-audio" style="display:none;">
                <div style="color: var(--accent-primary); font-weight: 600; margin-bottom: 15px; font-size: 14px; text-transform: uppercase; letter-spacing: 1px;">Mezclador de Audio</div>
                
                <div class="setting-group">
                    <label>Volumen de tu Voz (Micrófono)</label>
                    <div style="display:flex; align-items:center; gap:10px;">
                        <input type="range" id="vol-voz" min="0" max="2" step="0.1" value="1.0" style="flex:1;">
                        <span id="lbl-vol-voz" style="width:30px; font-size:12px; text-align:right;">1.0</span>
                    </div>
                    <p style="font-size:11px; color:#aaa; margin-top:5px;">Ajusta el volumen de la pista 2.</p>
                </div>

                <div class="setting-group">
                    <label>Volumen del Juego</label>
                    <div style="display:flex; align-items:center; gap:10px;">
                        <input type="range" id="vol-juego" min="0" max="2" step="0.1" value="1.0" style="flex:1;">
                        <span id="lbl-vol-juego" style="width:30px; font-size:12px; text-align:right;">1.0</span>
                    </div>
                    <p style="font-size:11px; color:#aaa; margin-top:5px;">Ajusta el volumen de la pista 3.</p>
                </div>

                <button class="btn" style="background: var(--bg-hover); width:100%; margin-top:10px;" onclick="generateAudioPreview()">🎧 Generar Previsualización</button>
                
                <div id="audio-preview-container" style="display:none; margin-top:15px; padding:10px; background:#111; border-radius:8px;">
                    <p style="font-size:11px; color:#0f0; margin:0 0 10px 0;">Previsualización lista (mezcla rápida):</p>
                    <audio id="audio-preview-player" controls style="width:100%; height:30px;"></audio>
                </div>
            </div>
'''

if 'id="panel-audio"' not in html:
    # Find FINAL IMG div and insert before it
    # We will search for id="panel-final"
    idx = html.find('<div id="panel-final">')
    if idx != -1:
        # Find the comment before it if possible, but just inserting before is fine
        insert_idx = html.rfind('<!--', 0, idx)
        if insert_idx == -1: insert_idx = idx
        html = html[:insert_idx] + audio_panel_html + html[insert_idx:]

with open(r'c:\Users\leone\Desktop\OBS Grabaciones\Exports\Complete Games\templates\index.html', 'w', encoding='utf-8') as f:
    f.write(html)
