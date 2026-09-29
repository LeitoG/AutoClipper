with open('templates/index.html', 'r', encoding='utf-8') as f:
    text = f.read()

target = '''<p style="color:#888; font-size:12px; margin-bottom:15px;">Ttulo y Descripcin autogenerados por la IA.</p>'''
replacement = '''<p style="color:#888; font-size:12px; margin-bottom:15px;">Titulo y Descripcion autogenerados por la IA.</p>
                <button id="btn-regenerate-meta" class="btn" style="margin-bottom:15px; font-size:12px; padding:8px; background:#d09010; color:#000;" onclick="regenerateMetadata()"> Regenerar Metadatos con IA</button>'''

if target in text:
    text = text.replace(target, replacement)
    with open('templates/index.html', 'w', encoding='utf-8') as f:
        f.write(text)
    print("Done target 1")
else:
    print("Not found target 1")
