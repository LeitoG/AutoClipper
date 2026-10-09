with open('templates/index.html', 'r', encoding='utf-8') as f:
    text = f.read()

target = '''            <div style="margin-bottom: 15px;">
                <label style="display:flex; align-items:center; gap:8px; margin-bottom:5px; color:#ddd; cursor:pointer;">
                    <input type="checkbox" id="ai-opt-scare" checked> Sustos / Momentos de Terror
                </label>
                <label style="display:flex; align-items:center; gap:8px; margin-bottom:5px; color:#ddd; cursor:pointer;">
                    <input type="checkbox" id="ai-opt-funny" checked> Momentos Graciosos / Bugs / Bizarreadas
                </label>
                <label style="display:flex; align-items:center; gap:8px; margin-bottom:5px; color:#ddd; cursor:pointer;">
                    <input type="checkbox" id="ai-opt-story"> Explicaciones / Historias Turbias
                </label>
            </div>'''

replacement = '''            <div style="margin-bottom: 15px; display: grid; grid-template-columns: 1fr 1fr; gap: 10px;">
                <label style="display:flex; align-items:center; gap:8px; color:#ddd; cursor:pointer; font-size: 13px;">
                    <input type="checkbox" id="ai-opt-scare" checked> Sustos / Terror
                </label>
                <label style="display:flex; align-items:center; gap:8px; color:#ddd; cursor:pointer; font-size: 13px;">
                    <input type="checkbox" id="ai-opt-funny" checked> Graciosos / Bugs / Bizarreadas
                </label>
                <label style="display:flex; align-items:center; gap:8px; color:#ddd; cursor:pointer; font-size: 13px;">
                    <input type="checkbox" id="ai-opt-story" checked> Explicaciones / Historia / Lore
                </label>
                <label style="display:flex; align-items:center; gap:8px; color:#ddd; cursor:pointer; font-size: 13px;">
                    <input type="checkbox" id="ai-opt-emotional" checked> Emocionantes / Emotivos
                </label>
                <label style="display:flex; align-items:center; gap:8px; color:#ddd; cursor:pointer; font-size: 13px;">
                    <input type="checkbox" id="ai-opt-anecdotes" checked> Anécdotas / Preguntas Viewers
                </label>
                <label style="display:flex; align-items:center; gap:8px; color:#ddd; cursor:pointer; font-size: 13px;">
                    <input type="checkbox" id="ai-opt-bosses" checked> Peleas contra Bosses / Jefes
                </label>
                <label style="display:flex; align-items:center; gap:8px; color:#ddd; cursor:pointer; font-size: 13px;">
                    <input type="checkbox" id="ai-opt-tension" checked> Momentos de Tensión jugando
                </label>
            </div>'''

text = text.replace(target, replacement)

target2 = '''            if(document.getElementById('ai-opt-scare').checked) prompt += "[Sustos/Terror] ";
            if(document.getElementById('ai-opt-funny').checked) prompt += "[Gracioso/Bugs] ";
            if(document.getElementById('ai-opt-story').checked) prompt += "[Historias/Explicativo] ";'''

replacement2 = '''            if(document.getElementById('ai-opt-scare').checked) prompt += "[Sustos/Terror] ";
            if(document.getElementById('ai-opt-funny').checked) prompt += "[Gracioso/Bugs] ";
            if(document.getElementById('ai-opt-story').checked) prompt += "[Historias/Lore/Explicativo] ";
            if(document.getElementById('ai-opt-emotional').checked) prompt += "[Emocionantes/Emotivos] ";
            if(document.getElementById('ai-opt-anecdotes').checked) prompt += "[Anécdotas/Preguntas Viewers] ";
            if(document.getElementById('ai-opt-bosses').checked) prompt += "[Peleas/Jefes/Bosses] ";
            if(document.getElementById('ai-opt-tension').checked) prompt += "[Tensión jugando] ";'''

text = text.replace(target2, replacement2)

target3 = '''                // Si buscan historias, usamos el motor semntico
                if (document.getElementById('ai-opt-story').checked) {
                    searchModes.push('semantic');
                }'''

replacement3 = '''                // Si buscan cosas complejas, usamos el motor semntico
                if (document.getElementById('ai-opt-story').checked || document.getElementById('ai-opt-emotional').checked || document.getElementById('ai-opt-anecdotes').checked || document.getElementById('ai-opt-bosses').checked || document.getElementById('ai-opt-tension').checked) {
                    searchModes.push('semantic');
                }'''

text = text.replace(target3, replacement3)

with open('templates/index.html', 'w', encoding='utf-8') as f:
    f.write(text)
print("Updated AI UI and prompt generation")
