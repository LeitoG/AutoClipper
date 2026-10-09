with open('templates/index.html', 'r', encoding='utf-8') as f:
    text = f.read()

target = '''                        <div style="display: flex; gap: 10px; margin-top: 10px; align-items: stretch;">
                            <button class="btn" style="background:#cc3333; flex: 1; margin:0;" onclick="discardClip('', event)">Descartar</button>
                            <button class="btn" style="background:#d09010; flex: 1; margin:0;" onclick="enterTrimMode('', event)">Modo Edición</button>
                        </div>
                    ;    <div id="controls-" style="display:none; flex-direction:column; gap:8px; margin-top: 15px; background: #1a1a1a; padding: 12px; border-radius: 4px; border: 1px solid #444;">
                             <div style="font-size: 11px; color: #aaa; text-align: center; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 2px;">Ajuste de Precisin</div>'''

replacement = '''                        <div style="display: flex; gap: 10px; margin-top: 10px; align-items: stretch;">
                            <button class="btn" style="background:#cc3333; flex: 1; margin:0;" onclick="discardClip('', event)">Descartar</button>
                            <button class="btn" style="background:#d09010; flex: 1; margin:0;" onclick="enterTrimMode('', event)">Modo Edición</button>
                        </div>
                        <div id="controls-" style="display:none; flex-direction:column; gap:8px; margin-top: 15px; background: #1a1a1a; padding: 12px; border-radius: 4px; border: 1px solid #444;">
                             <div style="font-size: 11px; color: #aaa; text-align: center; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 2px;">Ajuste de Precisin</div>'''

text = text.replace(target, replacement)
text = text.replace('clipsData.forEach(clip => {', 'clipsData.forEach((clip, idx) => {')

with open('templates/index.html', 'w', encoding='utf-8') as f:
    f.write(text)
print("Fixed template literal")
