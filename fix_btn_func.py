with open('templates/index.html', 'r', encoding='utf-8') as f:
    text = f.read()

func = '''
        async function regenerateMetadata() {
            const btn = document.getElementById('btn-regenerate-meta');
            const originalText = btn.innerText;
            
            // Collect words from editorWords or just use full clip transcript if empty
            let transcriptText = "";
            if (editorWords && editorWords.length > 0) {
                transcriptText = editorWords.map(w => w.word).join(" ");
            } else if (currentClip && currentClip.transcript) {
                transcriptText = currentClip.transcript;
            } else {
                alert("No hay subtitulos ni transcripcion para regenerar los metadatos. Primero transcribe el clip.");
                return;
            }
            
            btn.innerText = "Regenerando con IA...";
            btn.disabled = true;
            
            try {
                const res = await fetch('/regenerate_metadata', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        video_name: videoName,
                        transcript: transcriptText
                    })
                });
                const data = await res.json();
                if (data.status === 'success') {
                    if (data.social_title) {
                        document.getElementById('redes-titulo').value = data.social_title;
                        currentClip.social_title = data.social_title;
                    }
                    if (data.social_desc) {
                        document.getElementById('redes-desc').value = data.social_desc;
                        currentClip.social_desc = data.social_desc;
                    }
                    saveCurrentClipState();
                } else {
                    alert('Error regenerando metadatos: ' + data.message);
                }
            } catch (err) {
                alert('Error en la conexion: ' + err);
            } finally {
                btn.innerText = originalText;
                btn.disabled = false;
            }
        }

'''

target = "let transcribeController = null;"
text = text.replace(target, func + target)

with open('templates/index.html', 'w', encoding='utf-8') as f:
    f.write(text)
print("Done function")
