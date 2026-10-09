with open('templates/index.html', 'r', encoding='utf-8') as f:
    text = f.read()

target = '''            workspaceVideo.src = window.location.origin + "/videos/" + encodeURIComponent(videoName) + "#t=" + currentClip.start + "," + currentClip.end;
            let vUrl = "/get_clip_audio_track?video_name=" + encodeURIComponent(videoName) + "&start=" + currentClip.start + "&end=" + currentClip.end + "&track_index=1";
            let jUrl = "/get_clip_audio_track?video_name=" + encodeURIComponent(videoName) + "&start=" + currentClip.start + "&end=" + currentClip.end + "&track_index=2";
            document.getElementById('global-audio-voice').src = vUrl;
            document.getElementById('global-audio-game').src = jUrl;
            attachAudioSync(workspaceVideo, currentClip.start);
            workspaceVideo.play();'''

replacement = '''            workspaceVideo.src = window.location.origin + "/videos/" + encodeURIComponent(videoName) + "#t=" + currentClip.start + "," + currentClip.end;
            
            workspaceVideo.currentTime = currentClip.start;
            workspaceVideo.addEventListener('loadedmetadata', function() {
                if (Math.abs(workspaceVideo.currentTime - currentClip.start) > 1) {
                    workspaceVideo.currentTime = currentClip.start;
                }
            }, { once: true });
            
            let vUrl = "/get_clip_audio_track?video_name=" + encodeURIComponent(videoName) + "&start=" + currentClip.start + "&end=" + currentClip.end + "&track_index=1";
            let jUrl = "/get_clip_audio_track?video_name=" + encodeURIComponent(videoName) + "&start=" + currentClip.start + "&end=" + currentClip.end + "&track_index=2";
            document.getElementById('global-audio-voice').src = vUrl;
            document.getElementById('global-audio-game').src = jUrl;
            attachAudioSync(workspaceVideo, currentClip.start);
            workspaceVideo.play();'''

text = text.replace(target, replacement)

with open('templates/index.html', 'w', encoding='utf-8') as f:
    f.write(text)
print("workspaceVideo.currentTime forced")
