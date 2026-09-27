import re

with open(r'c:\Users\leone\Desktop\OBS Grabaciones\Exports\Complete Games\templates\index.html', 'r', encoding='utf-8') as f:
    text = f.read()

# 1. Add global audio tags
audio_tags = '''
    <audio id="global-audio-voice" style="display:none;"></audio>
    <audio id="global-audio-game" style="display:none;"></audio>
'''
if 'id="global-audio-voice"' not in text:
    text = text.replace('<div id="view-timeline">', audio_tags + '\n    <div id="view-timeline">')

# 2. Fix seekScrubber
old_seek = '''function seekScrubber(e) {
    if(!workspaceVideo || !workspaceVideo.duration) return;
    const rect = e.currentTarget.getBoundingClientRect();
    const perc = Math.max(0, Math.min(1, (e.clientX - rect.left) / rect.width));
    workspaceVideo.currentTime = perc * workspaceVideo.duration;
}'''
new_seek = '''function seekScrubber(e) {
    if(!workspaceVideo) return;
    const rect = e.currentTarget.getBoundingClientRect();
    const perc = Math.max(0, Math.min(1, (e.clientX - rect.left) / rect.width));
    if(typeof getTimelineDuration === "function") {
        workspaceVideo.currentTime = relToAbs(getTimelineDuration() * perc);
    } else {
        const totalDur = currentClip.end - currentClip.start;
        workspaceVideo.currentTime = currentClip.start + (totalDur * perc);
    }
}'''
text = text.replace(old_seek, new_seek)

with open(r'c:\Users\leone\Desktop\OBS Grabaciones\Exports\Complete Games\templates\index.html', 'w', encoding='utf-8') as f:
    f.write(text)
