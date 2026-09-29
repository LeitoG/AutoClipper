import re

with open('templates/index.html', 'r', encoding='utf-8') as f:
    text = f.read()

# Replace the persistence logic in loadVideosList
old_logic = '''                    let lastFolder = localStorage.getItem('lastFolder');
                    let isFirstLoad = !videoName;
                    
                    if (lastFolder && folders.has(lastFolder) && isFirstLoad) {
                        folderSel.value = lastFolder;
                    } else if (isFirstLoad) {
                        if (folderSel.options.length > 1) folderSel.selectedIndex = 1;
                    } else if (videoName) {
                        const parts = videoName.split('/');
                        folderSel.value = parts.length > 1 ? parts[0] : "Raz";
                    }
                    
                    updateVideoDropdown();
                    
                    let lastVideo = localStorage.getItem('lastVideo');
                    const videoSel = document.getElementById('video-selector');
                    
                    if (isFirstLoad) {
                        if (lastVideo) {
                            for (let i = 0; i < videoSel.options.length; i++) {
                                if (videoSel.options[i].value === lastVideo) {
                                    videoSel.selectedIndex = i;
                                    break;
                                }
                            }
                        }
                        if (videoSel.selectedIndex <= 0 && videoSel.options.length > 1) {
                            videoSel.selectedIndex = 1;
                        }
                        init();
                    }'''

new_logic = '''                    let lastFolder = localStorage.getItem('lastFolder');
                    let lastVideo = localStorage.getItem('lastVideo');
                    let isFirstLoad = !videoName;
                    
                    if (isFirstLoad) {
                        // Restaurar carpeta
                        if (lastFolder && folders.has(lastFolder)) {
                            folderSel.value = lastFolder;
                        } else {
                            if (folderSel.options.length > 1) folderSel.selectedIndex = 1;
                        }
                        
                        updateVideoDropdown();
                        
                        // Restaurar video
                        const videoSel = document.getElementById('video-selector');
                        let videoFound = false;
                        if (lastVideo) {
                            for (let i = 0; i < videoSel.options.length; i++) {
                                if (videoSel.options[i].value === lastVideo) {
                                    videoSel.selectedIndex = i;
                                    videoFound = true;
                                    break;
                                }
                            }
                        }
                        
                        // Si no encontr el video, quizs es de otra carpeta, seleccionamos el primero de la carpeta actual
                        if (!videoFound && videoSel.options.length > 1) {
                            videoSel.selectedIndex = 1;
                        }
                        
                        if (videoSel.value) {
                            init();
                        }
                    } else if (videoName) {
                        const parts = videoName.split('/');
                        folderSel.value = parts.length > 1 ? parts[0] : "Raz";
                        updateVideoDropdown();
                    }'''

if old_logic in text:
    text = text.replace(old_logic, new_logic)
    with open('templates/index.html', 'w', encoding='utf-8') as f:
        f.write(text)
    print("Replaced logic successfully")
else:
    print("Target logic not found")
