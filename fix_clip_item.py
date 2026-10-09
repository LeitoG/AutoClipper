with open('templates/index.html', 'r', encoding='utf-8') as f:
    text = f.read()

target = '''                    el.innerHTML = 
                        <div style="font-weight:bold; color:#007acc; font-size:18px; display:flex; justify-content:space-between; align-items:center;">
                            <div style="display:flex; align-items:center; gap:8px;">
                                <input type="checkbox" class="merge-checkbox" data-clip-id="" style="width:16px; height:16px; cursor:pointer;" onclick="event.stopPropagation()">
                                <span> <span style="font-size:12px; color:#aaa;"></span></span>
                            </div>
                            <div style="display:flex; align-items:center; gap:10px;">
                                <span style="cursor:pointer; font-size:16px; transition:0.2s; " onclick="giveFeedback('', 'up', event)" title="Buen clip"></span>
                                <span style="cursor:pointer; font-size:16px; transition:0.2s; " onclick="giveFeedback('', 'down', event)" title="Mal clip"></span>
                                
                            </div>
                        </div>
                        <input type="text" value="" placeholder="Sugerencia de IA" 
                                style="width:100%; font-size:13px; color:#ddd; margin-top:4px; font-style:italic; background:transparent; border:1px solid #444; padding:3px 5px; border-radius:3px; outline:none;" 
                                onchange="updateClipReason('', this.value)" onclick="event.stopPropagation()">
                        <div style="font-size:0.85em; color:#aaa; margin-top:5px;" id="times-"> -  <span style="color:#fff; font-weight:bold;">(s)</span></div>
                        <div style="display: flex; gap: 10px; margin-top: 10px; align-items: stretch;">
                            <button class="btn" style="background:#d09010; flex: 1; margin:0;" onclick="enterTrimMode('', event)">Modo Edicin</button>
                            
                        </div>'''

replacement = '''                    el.innerHTML = 
                        <div style="font-weight:bold; color:#007acc; font-size:18px; display:flex; justify-content:space-between; align-items:center;">
                            <div style="display:flex; align-items:center; gap:8px;">
                                <input type="checkbox" class="merge-checkbox" data-clip-id="" style="width:16px; height:16px; cursor:pointer;" onclick="event.stopPropagation()">
                                <span>Clip  <span style="font-size:12px; color:#aaa;">()</span></span>
                            </div>
                            <div style="display:flex; align-items:center; gap:10px;">
                                <span style="cursor:pointer; font-size:16px; transition:0.2s; " onclick="giveFeedback('', 'up', event)" title="Buen clip">??</span>
                                <span style="cursor:pointer; font-size:16px; transition:0.2s; " onclick="giveFeedback('', 'down', event)" title="Mal clip">??</span>
                                
                            </div>
                        </div>
                        <input type="text" value="" placeholder="Sugerencia de IA" 
                                style="width:100%; font-size:13px; color:#ddd; margin-top:4px; font-style:italic; background:transparent; border:1px solid #444; padding:3px 5px; border-radius:3px; outline:none;" 
                                onchange="updateClipReason('', this.value)" onclick="event.stopPropagation()">
                        <div style="font-size:0.85em; color:#aaa; margin-top:5px;" id="times-"> -  <span style="color:#fff; font-weight:bold;">(s)</span></div>
                        <div style="display: flex; gap: 10px; margin-top: 10px; align-items: stretch;">
                            <button class="btn" style="background:#cc3333; flex: 1; margin:0;" onclick="discardClip('', event)">Descartar</button>
                            <button class="btn" style="background:#d09010; flex: 1; margin:0;" onclick="enterTrimMode('', event)">Modo Edición</button>
                        </div>'''

text = text.replace(target, replacement)
text = text.replace('clipsData.forEach(clip => {', 'clipsData.forEach((clip, idx) => {')

with open('templates/index.html', 'w', encoding='utf-8') as f:
    f.write(text)
print("Updated clip item HTML")
