import re

with open(r'c:\Users\leone\Desktop\OBS Grabaciones\Exports\Complete Games\templates\index.html', 'r', encoding='utf-8') as f:
    text = f.read()

# Add sync logic script
sync_script = '''
    <script>
        function updateAudioVolumes() {
            let v = document.getElementById('vol-voz') ? parseFloat(document.getElementById('vol-voz').value) : 1.0;
            let j = document.getElementById('vol-juego') ? parseFloat(document.getElementById('vol-juego').value) : 1.0;
            document.getElementById('global-audio-voice').volume = v;
            document.getElementById('global-audio-game').volume = j;
            if (document.getElementById('lbl-vol-voz')) document.getElementById('lbl-vol-voz').innerText = v.toFixed(1);
            if (document.getElementById('lbl-vol-juego')) document.getElementById('lbl-vol-juego').innerText = j.toFixed(1);
        }
        
        function attachAudioSync(videoEl, clipStart) {
            videoEl.muted = true;
            let vAudio = document.getElementById('global-audio-voice');
            let jAudio = document.getElementById('global-audio-game');
            
            videoEl.onplay = () => { vAudio.play().catch(e=>{}); jAudio.play().catch(e=>{}); };
            videoEl.onpause = () => { vAudio.pause(); jAudio.pause(); };
            videoEl.onseeked = () => {
                let rel = videoEl.currentTime - clipStart;
                vAudio.currentTime = rel;
                jAudio.currentTime = rel;
            };
            videoEl.onratechange = () => {
                vAudio.playbackRate = videoEl.playbackRate;
                jAudio.playbackRate = videoEl.playbackRate;
            };
        }

        // Hook sliders
        document.addEventListener('DOMContentLoaded', () => {
            let vv = document.getElementById('vol-voz');
            let vj = document.getElementById('vol-juego');
            if (vv) vv.addEventListener('input', updateAudioVolumes);
            if (vj) vj.addEventListener('input', updateAudioVolumes);
        });
    </script>
'''

if 'function updateAudioVolumes()' not in text:
    text = text.replace('</body>', sync_script + '\n</body>')

# Patch openTrimmer to load audio tracks
open_trimmer_hook = '''
            trimmerVideo.src = /videos/#t=,;
            
            // Cargar pistas de audio
            document.getElementById('global-audio-voice').src = /get_clip_audio_track?video_name=&start=&end=&track_index=1;
            document.getElementById('global-audio-game').src = /get_clip_audio_track?video_name=&start=&end=&track_index=2;
            attachAudioSync(trimmerVideo, clip.start);
            updateAudioVolumes();
'''
text = re.sub(r'trimmerVideo\.src\s*=\s*/videos/\$\{videoName\}#t=\$\{clip\.start\},\$\{clip\.end\};', open_trimmer_hook, text)

# Patch proceedToLayoutMode to use workspaceVideo
proceed_hook = '''
            workspaceVideo.src = /videos/#t=,;
            attachAudioSync(workspaceVideo, currentClip.start);
            updateAudioVolumes();
'''
text = re.sub(r'workspaceVideo\.src\s*=\s*/videos/\$\{videoName\}#t=\$\{currentClip\.start\},\$\{currentClip\.end\};', proceed_hook, text)

with open(r'c:\Users\leone\Desktop\OBS Grabaciones\Exports\Complete Games\templates\index.html', 'w', encoding='utf-8') as f:
    f.write(text)
