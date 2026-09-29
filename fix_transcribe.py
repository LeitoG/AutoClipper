with open('templates/index.html', 'r', encoding='utf-8') as f:
    text = f.read()

target = '''                document.getElementById('ass-text').value = editorWords.map(w => w.text).join(' ');
                renderTimelineTracks();
                await saveCurrentClipState();
                
                btn.innerText = " Auto-Transcribir con IA";'''
replacement = '''                document.getElementById('ass-text').value = editorWords.map(w => w.text).join(' ');
                renderTimelineTracks();
                await saveCurrentClipState();
                
                // Regenerar t\u00edtulo y descripci\u00f3n en base a la nueva transcripci\u00f3n
                try {
                    toast.innerHTML = '<strong style="color:#d09010;"> IA Trabajando</strong><br><span style="font-size:12px;">Generando nuevos metadatos (t\u00edtulo y descripci\u00f3n)...</span>';
                    await regenerateMetadata();
                } catch(e) { console.error(e); }
                
                btn.innerText = " Auto-Transcribir con IA";'''

if target in text:
    text = text.replace(target, replacement)
    with open('templates/index.html', 'w', encoding='utf-8') as f:
        f.write(text)
    print("Done")
else:
    print("Not found")
