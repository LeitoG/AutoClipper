
        const errorContainer = document.getElementById('error-container');
        const clipListEl = document.getElementById('clip-list');
        const viewTimeline = document.getElementById('view-timeline');
        const viewEditor = document.getElementById('view-editor');
        const tlVideo = document.getElementById('tl-video');
        const workspaceVideo = document.getElementById('workspace-video');
        const previewCanvas = document.getElementById('preview-canvas');
        const ctxPreview = previewCanvas ? previewCanvas.getContext('2d') : null;
        
        let clipsData = [];
        let completedClipsData = [];
        let currentClip = null;
        let videoName = "";
        let stopListener = null;

        function formatTime(totalSeconds) {
            const h = Math.floor(totalSeconds / 3600);
            const m = Math.floor((totalSeconds % 3600) / 60);
            const s = Math.floor(totalSeconds % 60);
            if (h > 0) return `${h.toString().padStart(2, '0')}:${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
            return `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
        }

        async function init() {
            try {
                const res = await fetch('/clips', { cache: 'no-store' });
                const json = await res.json();
                
                if (json.status === "error") {
                    showError(json.message);
                    return;
                }
                
                clipsData = json.data.clips;
                completedClipsData = json.data.completed_clips || [];
                videoName = json.data.video_name;
                
                const dynamicVideoUrl = "http://localhost:8000/videos/" + videoName;
                if (tlVideo.src !== dynamicVideoUrl) {
                    tlVideo.src = dynamicVideoUrl;
                }
                
                renderSidebar();
                if (tlVideo.readyState >= 1) {
                    drawTimelineDots();
                } else {
                    tlVideo.addEventListener('loadedmetadata', drawTimelineDots);
                }
            } catch (err) {
                showError("No se pudo conectar con FastAPI. " + err.message);
            }
        }

        function drawTimelineDots() {
            const container = document.getElementById('timeline-dots');
            if (!container) return;
            container.innerHTML = '';
            const duration = tlVideo.duration;
            if (!duration || isNaN(duration)) return;
            
            clipsData.forEach(clip => {
                const perc = (clip.start / duration) * 100;
                const dot = document.createElement('div');
                dot.className = 'timeline-dot';
                dot.dataset.start = clip.start;
                dot.dataset.end = clip.end;
                dot.style.position = 'absolute';
                dot.style.left = `${perc}%`;
                dot.style.top = '-4px';
                dot.style.width = '14px';
                dot.style.height = '14px';
                dot.style.borderRadius = '50%';
                dot.style.background = '#aa55ff';
                dot.style.transform = 'translateX(-50%)';
                dot.style.cursor = 'pointer';
                dot.style.boxShadow = '0 0 5px rgba(170, 85, 255, 0.8)';
                dot.onclick = (e) => {
                    e.stopPropagation();
                    focusClip(clip);
                };
                container.appendChild(dot);
            });
            
            completedClipsData.forEach(clip => {
                const perc = (clip.start / duration) * 100;
                const dot = document.createElement('div');
                dot.style.position = 'absolute';
                dot.style.left = `${perc}%`;
                dot.style.top = '-2px';
                dot.style.width = '10px';
                dot.style.height = '10px';
                dot.style.borderRadius = '50%';
                dot.style.background = '#4CAF50';
                dot.style.transform = 'translateX(-50%)';
                container.appendChild(dot);
            });
        }

        function showError(msg) {
            errorContainer.innerHTML = `<div class="error-alert">🚨 Error Fatal: ${msg}</div>`;
            clipListEl.innerHTML = "";
        }

        function renderSidebar() {
            clipListEl.innerHTML = '';
            if(clipsData.length === 0) {
                clipListEl.innerHTML = `<div style="color:#aaa;">No hay clips pendientes.</div>`;
            } else {
                clipsData.forEach(clip => {
                    const virality = clip.virality_score ? `<span style="color:#28a745; float:right; font-size: 14px;">🔥 ${clip.virality_score}% Viral</span>` : '';
                    const duration = (clip.end - clip.start).toFixed(1);
                    const el = document.createElement('div');
                    el.className = 'clip-item';
                    el.id = `clip-item-${clip.id}`;
                    el.innerHTML = `
                        <div style="font-weight:bold; color:#007acc; font-size:18px;">${clip.id} ${virality}</div>
                        <div style="font-size:13px; color:#ddd; margin-top:4px; font-style:italic;">"${clip.reason || 'Sugerencia de IA'}"</div>
                        <div style="font-size:0.85em; color:#aaa; margin-top:5px;" id="times-${clip.id}">${formatTime(clip.start)} - ${formatTime(clip.end)} <span style="color:#fff; font-weight:bold;">(${duration}s)</span></div>
                        <div style="display: flex; gap: 10px; margin-top: 10px; align-items: stretch;">
                            <button class="btn" style="background:#d09010; flex: 1; margin:0;" onclick="enterTrimMode('${clip.id}', event)">Modo Edición</button>
                            <label style="display:flex; align-items:center; background:#444; padding: 0 10px; border-radius:4px; cursor:pointer;" onclick="event.stopPropagation()">
                                <input type="checkbox" onchange="markClipDone('${clip.id}', this)" style="margin-right:5px; width:16px; height:16px; cursor:pointer;"> Listo
                            </label>
                        </div>
                        <div id="controls-${clip.id}" style="display:none; flex-direction:column; gap:8px; margin-top: 15px; background: #1a1a1a; padding: 12px; border-radius: 4px; border: 1px solid #444;">
                            <div style="font-size: 11px; color: #aaa; text-align: center; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 2px;">Ajuste de Precisión</div>
                            <div style="display: flex; gap: 10px;">
                                <button class="btn" style="flex:1; background:#333; font-size:12px; padding:8px 0; margin:0; border: 1px solid #555;" onclick="setClipStart('${clip.id}', event)">⏮ Marcar Inicio</button>
                                <button class="btn" style="flex:1; background:#333; font-size:12px; padding:8px 0; margin:0; border: 1px solid #555;" onclick="setClipEnd('${clip.id}', event)">Marcar Final ⏭</button>
                            </div>
                        </div>
                    `;
                    el.onclick = () => focusClip(clip);
                    clipListEl.appendChild(el);
                });
            }
            
            const completedListEl = document.getElementById('completed-clip-list');
            completedListEl.innerHTML = '';
            if(completedClipsData.length === 0) {
                completedListEl.innerHTML = `<div style="color:#aaa;">No hay clips editados.</div>`;
            } else {
                completedClipsData.forEach(clip => {
                    const el = document.createElement('div');
                    el.className = 'clip-item';
                    el.style.opacity = '0.7';
                    el.innerHTML = `
                        <div style="font-weight:bold; color:#28a745; font-size:16px;">✅ ${clip.id}</div>
                        <div style="font-size:0.85em; color:#aaa; margin-top:5px;">${formatTime(clip.start)} - ${formatTime(clip.end)}</div>
                        <button class="btn" style="background:#444; margin-top:10px; padding: 5px;" onclick="restoreClip('${clip.id}', event)">↩️ Restaurar / Re-editar</button>
                    `;
                    completedListEl.appendChild(el);
                });
            }
        }

        function focusClip(clip) {
            currentClip = clip;
            tlVideo.currentTime = clip.start;
            
            // Reset styles
            clipsData.forEach(c => {
                const ctrl = document.getElementById(`controls-${c.id}`);
                if (ctrl) ctrl.style.display = 'none';
                const item = document.getElementById(`clip-item-${c.id}`);
                if (item) item.style.border = 'none';
            });
            
            // Highlight selected
            const ctrl = document.getElementById(`controls-${clip.id}`);
            if (ctrl) ctrl.style.display = 'flex';
            const item = document.getElementById(`clip-item-${clip.id}`);
            if (item) {
                item.style.border = '2px solid #aa55ff';
                item.scrollIntoView({ behavior: 'smooth', block: 'center' });
            }
            
            if (stopListener) tlVideo.removeEventListener('timeupdate', stopListener);
            stopListener = () => {
                if (tlVideo.currentTime >= clip.end) {
                    tlVideo.pause();
                }
            };
            tlVideo.addEventListener('timeupdate', stopListener);
        }

        function setClipStart(clipId, event) {
            event.stopPropagation();
            const clip = clipsData.find(c => c.id === clipId);
            if (clip) {
                clip.start = tlVideo.currentTime;
                if (clip.start >= clip.end) clip.end = clip.start + 5; // Sanity check
                updateClipTimes(clip);
            }
        }
        
        function setClipEnd(clipId, event) {
            event.stopPropagation();
            const clip = clipsData.find(c => c.id === clipId);
            if (clip) {
                clip.end = tlVideo.currentTime;
                if (clip.end <= clip.start) clip.start = clip.end - 5; // Sanity check
                updateClipTimes(clip);
            }
        }
        
        function updateClipTimes(clip) {
            const duration = (clip.end - clip.start).toFixed(1);
            const timesEl = document.getElementById(`times-${clip.id}`);
            if (timesEl) timesEl.innerHTML = `${formatTime(clip.start)} - ${formatTime(clip.end)} <span style="color:#fff; font-weight:bold;">(${duration}s)</span>`;
            drawTimelineDots();
        }

        // --- LOGICA DEL TRIMMER (V17) ---
        const viewTrimmer = document.getElementById('view-trimmer');
        const trimmerVideo = document.getElementById('trimmer-video');
        let trimmerZoomStart = 0;
        let trimmerZoomEnd = 0;
        let isDraggingStart = false;
        let isDraggingEnd = false;
        let trimLoopId = null;

        async function enterTrimMode(clipId, event) {
            if (event) event.stopPropagation();
            currentClip = clipsData.find(c => c.id === clipId) || completedClipsData.find(c => c.id === clipId);
            
            document.getElementById('trimmer-clip-name').innerText = currentClip.id;
            
            viewTimeline.classList.add('hidden');
            viewTrimmer.style.display = 'flex'; // Oculta el Grid del layout
            
            tlVideo.pause();
            
            // Definir ventana de zoom: +/- 60 segundos
            trimmerZoomStart = Math.max(0, currentClip.start - 60);
            trimmerZoomEnd = Math.min(tlVideo.duration || 9999, currentClip.end + 60);
            
            document.getElementById('trimmer-zoom-start').innerText = formatTime(trimmerZoomStart);
            document.getElementById('trimmer-zoom-end').innerText = formatTime(trimmerZoomEnd);
            
            trimmerVideo.src = `/videos/${videoName}#t=${trimmerZoomStart},${trimmerZoomEnd}`;
            trimmerVideo.currentTime = currentClip.start;
            trimmerVideo.play();
            
            updateTrimmerVisuals();
            
            if(!trimLoopId) trimLoopId = requestAnimationFrame(trimmerLoop);
        }

        function exitTrimmerMode() {
            viewTrimmer.style.display = 'none';
            viewTimeline.classList.remove('hidden');
            trimmerVideo.pause();
            cancelAnimationFrame(trimLoopId);
            trimLoopId = null;
        }

        function proceedToLayoutMode() {
            viewTrimmer.style.display = 'none';
            trimmerVideo.pause();
            cancelAnimationFrame(trimLoopId);
            trimLoopId = null;
            enterEditMode(currentClip.id, null);
        }

        function trimmerLoop() {
            if (viewTrimmer.style.display !== 'none' && trimmerVideo.duration) {
                const dur = trimmerZoomEnd - trimmerZoomStart;
                const perc = ((trimmerVideo.currentTime - trimmerZoomStart) / dur) * 100;
                const ph = document.getElementById('trimmer-playhead');
                if(ph) ph.style.left = `${Math.max(0, Math.min(100, perc))}%`;
                
                // Frenar al final del clip
                if (trimmerVideo.currentTime >= currentClip.end && !trimmerVideo.paused) {
                    trimmerVideo.pause();
                    trimmerVideo.currentTime = currentClip.end;
                }
            }
            trimLoopId = requestAnimationFrame(trimmerLoop);
        }

        function updateTrimmerVisuals() {
            const dur = trimmerZoomEnd - trimmerZoomStart;
            if(dur <= 0) return;
            
            const startPerc = Math.max(0, Math.min(100, ((currentClip.start - trimmerZoomStart) / dur) * 100));
            const endPerc = Math.max(0, Math.min(100, ((currentClip.end - trimmerZoomStart) / dur) * 100));
            
            const sel = document.getElementById('trimmer-selection');
            if(sel) {
                sel.style.left = `${startPerc}%`;
                sel.style.width = `${endPerc - startPerc}%`;
            }
            
            const hStart = document.getElementById('trimmer-handle-start');
            if(hStart) hStart.style.left = `${startPerc}%`;
            
            const hEnd = document.getElementById('trimmer-handle-end');
            if(hEnd) hEnd.style.left = `${endPerc}%`;
            
            const durEl = document.getElementById('trimmer-duration');
            if(durEl) durEl.innerText = (currentClip.end - currentClip.start).toFixed(1);
        }

        // Delay para enganchar eventos del trimmer cuando el DOM este listo
        setTimeout(() => {
            const tTimeline = document.getElementById('trimmer-timeline');
            if(!tTimeline) return;
            
            document.getElementById('trimmer-handle-start').addEventListener('mousedown', (e) => { isDraggingStart = true; e.preventDefault(); });
            document.getElementById('trimmer-handle-end').addEventListener('mousedown', (e) => { isDraggingEnd = true; e.preventDefault(); });
            
            document.addEventListener('mousemove', (e) => {
                if(!isDraggingStart && !isDraggingEnd) return;
                
                const rect = tTimeline.getBoundingClientRect();
                let perc = (e.clientX - rect.left) / rect.width;
                perc = Math.max(0, Math.min(1, perc));
                
                const dur = trimmerZoomEnd - trimmerZoomStart;
                const time = trimmerZoomStart + (perc * dur);
                
                if(isDraggingStart) {
                    currentClip.start = Math.min(time, currentClip.end - 1);
                    trimmerVideo.currentTime = currentClip.start;
                } else if(isDraggingEnd) {
                    currentClip.end = Math.max(time, currentClip.start + 1);
                    trimmerVideo.currentTime = currentClip.end;
                }
                
                updateTrimmerVisuals();
                updateClipTimes(currentClip);
            });
            
            document.addEventListener('mouseup', () => {
                isDraggingStart = false;
                isDraggingEnd = false;
            });
            
            tTimeline.addEventListener('click', (e) => {
                if(isDraggingStart || isDraggingEnd) return;
                const rect = tTimeline.getBoundingClientRect();
                let perc = (e.clientX - rect.left) / rect.width;
                const time = trimmerZoomStart + (perc * (trimmerZoomEnd - trimmerZoomStart));
                trimmerVideo.currentTime = time;
            });
        }, 500);

        // --- LOGICA DEL EDITOR DE ENCUADRE AVANZADO (V16) ---
        
        let renderLoopId;
        let currentTemplate = 'face_game';
        let cropState = {
            face: { x: 1500, y: 600, w: 420, h: 480 },
            game: { x: 420, y: 0, w: 1080, h: 1080 },
            full: { x: 420, y: 0, w: 1080, h: 1920 }
        };
        let canvasSplitY = 960; // Mitad por defecto
        const VID_W = 1920;
        const VID_H = 1080;
        window.fitMode = 'cover';
        
        function drawSmartFit(ctx, video, sx, sy, sw, sh, dx, dy, dw, dh) {
            ctx.save();
            ctx.beginPath();
            ctx.rect(dx, dy, dw, dh);
            ctx.clip();
            
            if (window.fitMode === 'contain') {
                ctx.filter = 'blur(20px) brightness(0.3)';
                ctx.drawImage(video, sx, sy, sw, sh, dx - 20, dy - 20, dw + 40, dh + 40);
            } else {
                ctx.fillStyle = '#000';
                ctx.fillRect(dx, dy, dw, dh);
            }
            
            ctx.filter = 'none';
            const scale = (window.fitMode === 'cover') ? Math.max(dw / sw, dh / sh) : Math.min(dw / sw, dh / sh);
            const drawW = sw * scale;
            const drawH = sh * scale;
            const drawX = dx + (dw - drawW) / 2;
            const drawY = dy + (dh - drawH) / 2;
            
            ctx.drawImage(video, sx, sy, sw, sh, drawX, drawY, drawW, drawH);
            ctx.restore();
        }

        function setTemplate(tpl) {
            currentTemplate = tpl;
            document.getElementById('tpl-face-game').style.borderColor = (tpl === 'face_game') ? '#aa55ff' : 'transparent';
            document.getElementById('tpl-fullscreen').style.borderColor = (tpl === 'fullscreen') ? '#2196F3' : 'transparent';
            
            document.getElementById('crop-face').style.display = (tpl === 'face_game') ? 'block' : 'none';
            document.getElementById('crop-game').style.display = (tpl === 'face_game') ? 'block' : 'none';
            document.getElementById('crop-full').style.display = (tpl === 'fullscreen') ? 'block' : 'none';
            document.getElementById('crop-subs').style.display = 'block'; // Siempre visible
            
            if (editorScenes[activeSceneId]) {
                editorScenes[activeSceneId].template = tpl;
                renderTimelineTracks();
            }
        }
        
        function updateWorkspaceAudioBtn() {
            const btn = document.getElementById('workspace-audio-btn');
            if(btn && workspaceVideo) {
                btn.innerText = workspaceVideo.muted ? "🔇 Audio Muteado" : "🔊 Audio Activado";
            }
        }
        
        function toggleWorkspaceAudio() {
            if(!workspaceVideo) return;
            workspaceVideo.muted = !workspaceVideo.muted;
            updateWorkspaceAudioBtn();
        }
        
        function togglePlayPauseWorkspace() {
            if(!workspaceVideo) return;
            if(workspaceVideo.paused) workspaceVideo.play();
            else workspaceVideo.pause();
        }
        
        function toggleVisibility(id, btn) {
            const el = document.getElementById(id);
            if (!el) return;
            if (el.style.opacity === '0') {
                el.style.opacity = '1';
                el.style.pointerEvents = 'auto';
                btn.style.opacity = '1';
            } else {
                el.style.opacity = '0';
                el.style.pointerEvents = 'none';
                btn.style.opacity = '0.5';
            }
        }
        
        function renderCanvasLoop() {
            try {
            if (viewEditor.style.display === 'none' || !ctxPreview) return;
            if(workspaceVideo.readyState < 2) {
                renderLoopId = requestAnimationFrame(renderCanvasLoop);
                return;
            }
            
            ctxPreview.fillStyle = '#000';
            ctxPreview.fillRect(0, 0, 1080, 1920);
            const activeScene = editorScenes.find(s => workspaceVideo.currentTime >= s.start && workspaceVideo.currentTime < s.end) || editorScenes[editorScenes.length - 1];
            if (activeScene && activeSceneId !== editorScenes.indexOf(activeScene)) {
                activeSceneId = editorScenes.indexOf(activeScene);
                setTemplate(activeScene.template); // Cambiar template auto
            }
            
            if (currentTemplate === 'face_game') {
                const cF = activeScene.cropState.face;
                const cG = activeScene.cropState.game;
                if (cF.w > 0 && cF.h > 0) drawSmartFit(ctxPreview, workspaceVideo, cF.x, cF.y, cF.w, cF.h, 0, 0, 1080, canvasSplitY);
                if (cG.w > 0 && cG.h > 0) drawSmartFit(ctxPreview, workspaceVideo, cG.x, cG.y, cG.w, cG.h, 0, canvasSplitY, 1080, 1920 - canvasSplitY);
                
                ctxPreview.fillStyle = 'rgba(170, 85, 255, 0.5)';
                ctxPreview.fillRect(0, canvasSplitY - 4, 1080, 8);
                
            } else if (currentTemplate === 'fullscreen') {
                const cC = activeScene.cropState.full;
                if (cC.w > 0 && cC.h > 0) drawSmartFit(ctxPreview, workspaceVideo, cC.x, cC.y, cC.w, cC.h, 0, 0, 1080, 1920);
            }
            
            // Render Subtitles (Word-by-word)
            // Render scrubber head position si el reproductor está corriendo
            const scrubberHead = document.getElementById('scrubber-head');
            if (scrubberHead) {
                const totalDur = currentClip.end - currentClip.start;
                const perc = (workspaceVideo.currentTime - currentClip.start) / totalDur;
                scrubberHead.style.left = (Math.max(0, Math.min(1, perc)) * 100) + '%';
            }
            
            const activeWord = editorWords.find(w => workspaceVideo.currentTime >= w.start && workspaceVideo.currentTime <= w.end);
            if (activeWord) {
                const cS = activeScene.cropState.subs;
                // Dibujar subtitulo dentro del bounds del Canvas equivalente al crop-subs original
                const scaleX = 1080 / 1920; 
                const scaleY = 1920 / 1080;
                
                ctxPreview.save();
                ctxPreview.font = "bold 80px 'Montserrat', sans-serif";
                ctxPreview.textAlign = "center";
                ctxPreview.textBaseline = "middle";
                ctxPreview.lineWidth = 15;
                ctxPreview.strokeStyle = "#000";
                
                const drawX = (cS.x + cS.w/2) * scaleX;
                const drawY = (cS.y + cS.h/2) * scaleY;
                
                ctxPreview.strokeText(activeWord.text, drawX, drawY);
                ctxPreview.fillStyle = "#ffaa00";
                ctxPreview.fillText(activeWord.text, drawX, drawY);
                ctxPreview.restore();
            }
            
            if (currentClip && workspaceVideo.duration) {
                const clipDur = currentClip.end - currentClip.start;
                const currProg = workspaceVideo.currentTime - currentClip.start;
                const perc = (currProg / clipDur) * 100;
                const ph = document.getElementById('editor-playhead');
                if (ph) ph.style.left = `${Math.max(0, Math.min(100, perc))}%`;
                
                // Loopear solo en la zona del clip
                if (workspaceVideo.currentTime >= currentClip.end) {
                    workspaceVideo.currentTime = currentClip.start;
                } else if (workspaceVideo.currentTime < currentClip.start) {
                    workspaceVideo.currentTime = currentClip.start;
                }
            }
            
            renderLoopId = requestAnimationFrame(renderCanvasLoop);
            } catch(e) {
                alert("Error renderCanvasLoop: " + e.stack);
            }
        }

        // --- INTERACTIVIDAD DEL CANVAS (SPLIT DRAG) ---
        const pCanvas = document.getElementById('preview-canvas');
        let isDraggingSplit = false;
        
        if (pCanvas) {
            pCanvas.addEventListener('mousedown', (e) => {
                if (currentTemplate !== 'face_game') return;
                const rect = pCanvas.getBoundingClientRect();
                const y = (e.clientY - rect.top) / rect.height * 1920;
                if (Math.abs(y - canvasSplitY) < 150) { // Tolerancia amplia por si escalan
                    isDraggingSplit = true;
                    pCanvas.style.cursor = 'ns-resize';
                }
            });
            
            document.addEventListener('mousemove', (e) => {
                if (!isDraggingSplit) return;
                const rect = pCanvas.getBoundingClientRect();
                let y = (e.clientY - rect.top) / rect.height * 1920;
                y = Math.max(300, Math.min(1620, y)); // Limitar márgenes (min 300px, max 1620px)
                canvasSplitY = y;
            });
            
            document.addEventListener('mouseup', () => {
                isDraggingSplit = false;
                pCanvas.style.cursor = 'default';
            });
            
            pCanvas.addEventListener('mousemove', (e) => {
                if (currentTemplate !== 'face_game' || isDraggingSplit) return;
                const rect = pCanvas.getBoundingClientRect();
                const y = (e.clientY - rect.top) / rect.height * 1920;
                if (Math.abs(y - canvasSplitY) < 150) {
                    pCanvas.style.cursor = 'ns-resize';
                } else {
                    pCanvas.style.cursor = 'default';
                }
            });
        }

        function updateCropBoxesVisuals() {
            const container = document.getElementById('workspace-container');
            if(!container) return;
            const cw = container.clientWidth;
            const ch = container.clientHeight;
            const scaleX = cw / VID_W;
            const scaleY = ch / VID_H;
            
            const applyVisual = (id, state) => {
                const el = document.getElementById(id);
                if(!el) return;
                el.style.left = `${state.x * scaleX}px`;
                el.style.top = `${state.y * scaleY}px`;
                el.style.width = `${state.w * scaleX}px`;
                el.style.height = `${state.h * scaleY}px`;
            };
            applyVisual('crop-face', editorScenes[activeSceneId].cropState.face);
            applyVisual('crop-game', editorScenes[activeSceneId].cropState.game);
            applyVisual('crop-full', editorScenes[activeSceneId].cropState.full);
            applyVisual('crop-subs', editorScenes[activeSceneId].cropState.subs);
        }
        window.addEventListener('resize', updateCropBoxesVisuals);

        let activeDraggableElements = new Set();
        function makeDraggable(elId, stateKey) {
            if(activeDraggableElements.has(elId)) return;
            activeDraggableElements.add(elId);
            
            const el = document.getElementById(elId);
            if(!el) return;
            let isDragging = false, isResizing = false;
            let startX, startY, sX, sY, sW, sH;
            
            el.addEventListener('mousedown', (e) => {
                const s = editorScenes[activeSceneId].cropState[stateKey];
                if(e.target.classList.contains('resize-handle')) {
                    isResizing = true;
                } else {
                    isDragging = true;
                }
                startX = e.clientX;
                startY = e.clientY;
                sX = s.x; sY = s.y; sW = s.w; sH = s.h;
                e.preventDefault();
            });
            
            document.addEventListener('mousemove', (e) => {
                if(!isDragging && !isResizing) return;
                const container = document.getElementById('workspace-container');
                const scaleX = VID_W / container.clientWidth;
                const scaleY = VID_H / container.clientHeight;
                const dx = (e.clientX - startX) * scaleX;
                const dy = (e.clientY - startY) * scaleY;
                const s = editorScenes[activeSceneId].cropState[stateKey];
                
                if(isDragging) {
                    s.x = Math.max(0, Math.min(VID_W - sW, sX + dx));
                    s.y = Math.max(0, Math.min(VID_H - sH, sY + dy));
                } else if(isResizing) {
                    s.w = Math.max(50, Math.min(VID_W - sX, sW + dx));
                    s.h = Math.max(50, Math.min(VID_H - sY, sH + dy));
                }
                updateCropBoxesVisuals();
            });
            document.addEventListener('mouseup', () => { isDragging = false; isResizing = false; });
        }

        let editorScenes = [];
        let activeSceneId = 0;
        let editorWords = [];

        async function enterEditMode(clipId, event) {
            try {
            if (event) event.stopPropagation();
            currentClip = clipsData.find(c => c.id === clipId) || completedClipsData.find(c => c.id === clipId);
            
            const sourceInfo = document.getElementById('workspace-source-info');
            if(sourceInfo) sourceInfo.innerHTML = 'Fuente 16:9 <span style="color:#d09010; font-weight:bold;">' + currentClip.id + '</span>';
            
            // Iniciar Escenas V19
            editorScenes = [{
                id: Date.now(),
                start: currentClip.start,
                end: currentClip.end,
                template: 'face_game',
                cropState: {
                    face: currentClip.facecam_coords || { x: 1500, y: 600, w: 420, h: 480 },
                    game: currentClip.gameplay_coords || { x: 420, y: 0, w: 1080, h: 1080 },
                    full: { x: 420, y: 0, w: 1080, h: 1920 },
                    subs: { x: 420, y: 800, w: 1080, h: 200 }
                }
            }];
            activeSceneId = 0;
            
            
            // Heredar estado de audio
            const tlVideo = document.getElementById('tl-video');
            workspaceVideo.muted = tlVideo ? tlVideo.muted : true;
            updateWorkspaceAudioBtn();

            // Iniciar palabras desde el texto guardado (o AI)
            if (currentClip.words && currentClip.words.length > 0) {
                editorWords = currentClip.words;
                document.getElementById('ass-text').value = currentClip.ass_text || editorWords.map(w => w.text).join(' ');
                renderTimelineTracks();
            } else if (!currentClip.ass_text || currentClip.ass_text.trim() === "") {
                runAIAutoTranscribe(); // Auto-transcribe al entrar si está vacío
            } else {
                document.getElementById('ass-text').value = currentClip.ass_text;
                syncSubtitlesFromText();
            }
            
            loadCustomTemplates();
            
            // Sincronizar dinámicamente cuando el usuario escriba
            document.getElementById('ass-text').addEventListener('input', syncSubtitlesFromText);
            
            renderTimelineTracks();
            
            viewTimeline.classList.add('hidden');
            viewEditor.style.display = 'grid'; // Grid layout for V16/V19
            
            tlVideo.pause();
            
            workspaceVideo.src = `/videos/${videoName}#t=${currentClip.start},${currentClip.end}`;
            workspaceVideo.play();
            
            setTemplate('face_game');
            
            setTimeout(() => {
                makeDraggable('crop-face', 'face');
                makeDraggable('crop-game', 'game');
                makeDraggable('crop-full', 'full');
                makeDraggable('crop-subs', 'subs');
                updateCropBoxesVisuals();
                renderLoopId = requestAnimationFrame(renderCanvasLoop);
            }, 300); // 300ms asegurados para que el CSS grid se aplique
            } catch(e) {
                alert("Error enterEditMode: " + e.stack);
                console.error(e);
            }
        }

        async function exitEditMode() {
            viewEditor.style.display = 'none';
            viewTimeline.classList.remove('hidden');
            workspaceVideo.pause();
            cancelAnimationFrame(renderLoopId);
        }

        async function exportClip() {
            const btn = document.getElementById('btn-export');
            btn.innerText = "Sincronizando Backend...";
            btn.disabled = true;
            
            try {
                const resUpd = await fetch('/update_clip', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        clip_id: currentClip.id,
                        ass_text: document.getElementById('ass-text').value
                    })
                });
                const jUpd = await resUpd.json();
                if(jUpd.status === "error") throw new Error(jUpd.message);
                
                btn.innerText = "Lanzando FFmpeg...";
                
                const payload = {
                    clip_id: currentClip.id,
                    video_name: videoName,
                    start: currentClip.start,
                    end: currentClip.end,
                    fit_mode: window.fitMode,
                    scenes: editorScenes,
                    words: editorWords
                };
                
                const resExp = await fetch('/export', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify(payload)
                });
                const jExp = await resExp.json();
                if(jExp.status === "error") throw new Error(jExp.message);
                
                btn.innerText = "✅ Render Iniciado Exitosamente";
                btn.style.background = "#28a745";
                setTimeout(() => {
                    btn.innerText = "🚀 Exportar a FFmpeg";
                    btn.style.background = "#FF4B4B";
                    btn.disabled = false;
                }, 4000);
                
            } catch (err) {
                alert("🚨 Backend Falló: " + err.message);
                btn.innerText = "🚀 Exportar a FFmpeg";
                btn.style.background = "#FF4B4B";
                btn.disabled = false;
            }
        }

        function renderTimelineTracks() {
            const sceneTrack = document.getElementById('scene-track');
            const subsTrack = document.getElementById('subs-track');
            if(!sceneTrack || !subsTrack) return;
            
            const totalDur = currentClip.end - currentClip.start;
            
            
            // Eventos del scrubber para arrastrar
            const scrubberTrack = document.getElementById('scrubber-track');
            let isScrubbing = false;
            
            scrubberTrack.onmousedown = (e) => {
                isScrubbing = true;
                doScrub(e);
            };
            document.addEventListener('mousemove', (e) => {
                if (isScrubbing) doScrub(e);
            });
            document.addEventListener('mouseup', () => {
                isScrubbing = false;
            });
            
            function doScrub(e) {
                const rect = scrubberTrack.getBoundingClientRect();
                let perc = (e.clientX - rect.left) / rect.width;
                perc = Math.max(0, Math.min(1, perc));
                workspaceVideo.currentTime = currentClip.start + (totalDur * perc);
                document.getElementById('scrubber-head').style.left = (perc * 100) + '%';
            }
            
            // Render Scenes
            sceneTrack.innerHTML = '';
            sceneTrack.onclick = (e) => {
                const rect = sceneTrack.getBoundingClientRect();
                const perc = (e.clientX - rect.left) / rect.width;
                workspaceVideo.currentTime = currentClip.start + (totalDur * perc);
            };
            
            editorScenes.forEach((scene, i) => {
                const sPerc = ((scene.start - currentClip.start) / totalDur) * 100;
                const wPerc = ((scene.end - scene.start) / totalDur) * 100;
                const isAct = i === activeSceneId;
                
                const el = document.createElement('div');
                el.style = `position: absolute; left: ${sPerc}%; width: ${wPerc}%; height: 100%; background: ${isAct ? '#aa55ff' : '#444'}; border-right: 1px solid #111; display: flex; align-items: center; justify-content: center; font-size: 10px; color: #fff; overflow: hidden;`;
                
                const label = document.createElement('div');
                label.innerText = `Escena ${i+1}`;
                label.style.cursor = 'pointer';
                label.style.width = '100%';
                label.style.textAlign = 'center';
                label.onclick = (e) => {
                    e.stopPropagation();
                    activeSceneId = i;
                    setTemplate(scene.template);
                    updateCropBoxesVisuals();
                    renderTimelineTracks();
                };
                el.appendChild(label);
                sceneTrack.appendChild(el);
            });
            
            // Render Words (Subtitles)
            subsTrack.innerHTML = '';
            subsTrack.onclick = (e) => {
                if (e.target !== subsTrack) return;
                const rect = subsTrack.getBoundingClientRect();
                const perc = (e.clientX - rect.left) / rect.width;
                workspaceVideo.currentTime = currentClip.start + (totalDur * perc);
            };
            
            editorWords.forEach((word, i) => {
                const sPerc = ((word.start - currentClip.start) / totalDur) * 100;
                const wPerc = ((word.end - word.start) / totalDur) * 100;
                
                const el = document.createElement('div');
                el.style = `position: absolute; left: ${sPerc}%; width: ${wPerc}%; height: 100%; background: #ffaa00; border: 1px solid #000; border-radius: 2px; color: #000; font-size: 9px; font-weight: bold; display: flex; align-items: center; justify-content: space-between; overflow: hidden;`;
                
                // Drag Handles
                const leftHandle = document.createElement('div');
                leftHandle.style = 'width: 5px; height: 100%; cursor: w-resize; background: rgba(0,0,0,0.2);';
                leftHandle.onmousedown = (e) => startWordDrag(e, word, 'left');
                
                const centerLabel = document.createElement('div');
                centerLabel.innerText = word.text;
                centerLabel.style = 'flex: 1; text-align: center; cursor: default;';
                
                const rightHandle = document.createElement('div');
                rightHandle.style = 'width: 5px; height: 100%; cursor: e-resize; background: rgba(0,0,0,0.2);';
                rightHandle.onmousedown = (e) => startWordDrag(e, word, 'right');
                
                el.appendChild(leftHandle);
                el.appendChild(centerLabel);
                el.appendChild(rightHandle);
                subsTrack.appendChild(el);
            });
        }
        
        function splitScene() {
            const cTime = workspaceVideo.currentTime;
            const currentSceneIndex = editorScenes.findIndex(s => cTime >= s.start && cTime < s.end);
            if (currentSceneIndex === -1) return;
            
            const sceneToSplit = editorScenes[currentSceneIndex];
            if (cTime - sceneToSplit.start < 0.5 || sceneToSplit.end - cTime < 0.5) {
                alert("No puedes cortar tan cerca de los bordes de la escena.");
                return;
            }
            
            const newScene = {
                id: Date.now(),
                start: cTime,
                end: sceneToSplit.end,
                template: sceneToSplit.template,
                cropState: JSON.parse(JSON.stringify(sceneToSplit.cropState))
            };
            
            sceneToSplit.end = cTime;
            editorScenes.splice(currentSceneIndex + 1, 0, newScene);
            renderTimelineTracks();
        }

        let customTemplates = JSON.parse(localStorage.getItem('customTemplates') || "[]");
        function loadCustomTemplates() {
            const container = document.getElementById('saved-templates-container');
            const btns = container.querySelectorAll('.custom-tpl-btn');
            btns.forEach(b => b.remove());
            
            customTemplates.forEach((t, i) => {
                const btn = document.createElement('button');
                btn.className = "btn custom-tpl-btn";
                btn.style = "width:100%; margin-bottom:10px; border: 2px solid transparent; background: #333; color: #d09010;";
                btn.innerText = t.name;
                btn.onclick = () => {
                    const scene = editorScenes[activeSceneId];
                    scene.cropState = JSON.parse(JSON.stringify(t.cropState));
                    updateCropBoxesVisuals();
                };
                container.appendChild(btn);
            });
        }
        
        function saveCustomTemplate() {
            const name = prompt("Nombre de la plantilla:");
            if(!name) return;
            const tpl = {
                name: name,
                cropState: JSON.parse(JSON.stringify(editorScenes[activeSceneId].cropState))
            };
            customTemplates.push(tpl);
            localStorage.setItem('customTemplates', JSON.stringify(customTemplates));
            loadCustomTemplates();
        }

        function syncSubtitlesFromText() {
            const rawText = document.getElementById('ass-text').value.trim();
            if (!rawText) {
                editorWords = [];
                renderTimelineTracks();
                return;
            }
            
            const rawWords = rawText.split(/\s+/);
            const wordDur = (currentClip.end - currentClip.start) / rawWords.length;
            
            const newEditorWords = [];
            rawWords.forEach((txt, i) => {
                if (editorWords[i]) {
                    // Preservar el timing si ya existia la palabra
                    newEditorWords.push({
                        ...editorWords[i],
                        text: txt
                    });
                } else {
                    // Si es una palabra nueva, calcular el tiempo uniformemente
                    newEditorWords.push({
                        id: i,
                        text: txt,
                        start: currentClip.start + (i * wordDur),
                        end: currentClip.start + ((i + 1) * wordDur)
                    });
                }
            });
            editorWords = newEditorWords;
            renderTimelineTracks();
            saveCurrentClipState();
        }
        
        async function saveCurrentClipState() {
            if(!currentClip) return;
            currentClip.words = editorWords;
            currentClip.ass_text = document.getElementById('ass-text').value;
            
            try {
                await fetch('/update_clip', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        clip_id: currentClip.id,
                        ass_text: currentClip.ass_text,
                        words: currentClip.words
                    })
                });
            } catch (err) {
                console.error("Error guardando state:", err);
            }
        }
        
        // --- DRAGGING LOGIC PARA WORDS ---
        let draggingWord = null;
        let draggingHandle = null;
        let dragStartX = 0;
        let dragStartVal = 0;
        
        function startWordDrag(e, word, handle) {
            e.stopPropagation();
            e.preventDefault();
            draggingWord = word;
            draggingHandle = handle;
            dragStartX = e.clientX;
            dragStartVal = handle === 'left' ? word.start : word.end;
            document.addEventListener('mousemove', onWordDrag);
            document.addEventListener('mouseup', onWordDragEnd);
        }
        
        function onWordDrag(e) {
            if(!draggingWord) return;
            const subsTrack = document.getElementById('subs-track');
            const totalDur = currentClip.end - currentClip.start;
            const trackWidth = subsTrack.getBoundingClientRect().width;
            
            const dx = e.clientX - dragStartX;
            const dt = (dx / trackWidth) * totalDur;
            
            if (draggingHandle === 'left') {
                draggingWord.start = Math.max(currentClip.start, Math.min(draggingWord.end - 0.1, dragStartVal + dt));
            } else {
                draggingWord.end = Math.max(draggingWord.start + 0.1, Math.min(currentClip.end, dragStartVal + dt));
            }
            renderTimelineTracks();
        }
        
        function onWordDragEnd() {
            if(draggingWord) saveCurrentClipState();
            draggingWord = null;
            document.removeEventListener('mousemove', onWordDrag);
            document.removeEventListener('mouseup', onWordDragEnd);
        }
        
        async function runAIAutoTranscribe() {
            const btn = document.getElementById('btn-transcribe');
            const originalText = btn.innerText;
            btn.innerText = "⏳ Extrayendo audio y transcribiendo (puede tardar unos segundos)...";
            btn.disabled = true;
            btn.style.background = "#555";
            
            try {
                const res = await fetch('/transcribe', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        clip_id: currentClip.id,
                        video_name: videoName,
                        start: currentClip.start,
                        end: currentClip.end
                    })
                });
                const data = await res.json();
                if(data.status === "error") throw new Error(data.message);
                
                // Actualizar words
                editorWords = data.words.map((w, i) => ({
                    id: i,
                    text: w.word,
                    start: w.start,
                    end: w.end
                }));
                
                // Rellenar textarea
                document.getElementById('ass-text').value = editorWords.map(w => w.text).join(' ');
                
                renderTimelineTracks();
                await saveCurrentClipState();
                
            } catch (err) {
                alert("Error al transcribir con IA: " + err.message);
            } finally {
                btn.innerText = originalText;
                btn.disabled = false;
                btn.style.background = "#673ab7";
            }
        }

        // --- Lógica IA Modal ---
        function openAiModal() {
            document.getElementById('ai-modal').classList.remove('hidden');
            document.getElementById('ai-prompt').value = "";
        }
        function closeAiModal() {
            document.getElementById('ai-modal').classList.add('hidden');
        }
        async function generateAiClips() {
            const prompt = document.getElementById('ai-prompt').value;
            if(!prompt) return;
            
            closeAiModal();
            
            // Mostrar pantalla de carga
            const loadingScreen = document.getElementById('ai-loading');
            const progressBar = document.getElementById('ai-progress-bar');
            const progressText = document.getElementById('ai-loading-text');
            
            loadingScreen.classList.remove('hidden');
            progressBar.style.width = '10%';
            progressText.innerText = "Enviando prompt semántico a la IA...";
            
            try {
                // Iniciar petición asíncrona sin bloquear la UI todavía
                const fetchPromise = fetch('/generate_clips', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ prompt: prompt })
                });

                // Simular animación de progreso mientras el backend procesa
                setTimeout(() => { progressBar.style.width = '40%'; progressText.innerText = "Buscando contexto en la transcripción..."; }, 1000);
                setTimeout(() => { progressBar.style.width = '70%'; progressText.innerText = "Evaluando porcentaje de viralidad..."; }, 2500);
                setTimeout(() => { progressBar.style.width = '90%'; progressText.innerText = "Generando cortes precisos..."; }, 3500);
                
                // Esperar a que el backend termine
                const res = await fetchPromise;
                const json = await res.json();
                
                if(json.status === "error") throw new Error(json.message);
                
                progressBar.style.width = '100%';
                progressText.innerText = "¡Clips generados exitosamente!";
                
                // Recargar toda la UI con los nuevos clips
                setTimeout(() => {
                    loadingScreen.classList.add('hidden');
                    init();
                }, 800);
                
            } catch (err) {
                alert("🚨 Error de IA: " + err.message);
                loadingScreen.classList.add('hidden');
            }
        }

        async function markClipDone(clipId, checkbox) {
            if (!checkbox) return;
            const itemEl = document.getElementById(`clip-item-${clipId}`);
            if(itemEl) {
                itemEl.style.opacity = '0.4';
                itemEl.style.pointerEvents = 'none';
            }
            checkbox.disabled = true;
            
            const clip = clipsData.find(c => c.id === clipId);
            
            try {
                const res = await fetch('/mark_clip_done', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ clip_id: clipId, start: clip.start, end: clip.end })
                });
                const json = await res.json();
                if (json.status === "error") throw new Error(json.message);
                
                // Forzar recarga visual para mover a completados y pintar de azul
                init();
                
            } catch (err) {
                alert("Error al marcar clip: " + err.message);
                if(itemEl) {
                    itemEl.style.opacity = '1';
                    itemEl.style.pointerEvents = 'auto';
                }
                checkbox.disabled = false;
                checkbox.checked = false;
            }
        }

        async function restoreClip(clipId, event) {
            if (event) event.stopPropagation();
            try {
                const res = await fetch('/unmark_clip_done', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ clip_id: clipId })
                });
                const json = await res.json();
                if (json.status === "error") throw new Error(json.message);
                
                init(); // Reload UI
            } catch (err) {
                alert("Error al restaurar clip: " + err.message);
            }
        }

        init();
        function updateSubtitlePreview() {
            // Se llama cuando cambia el select de color
        }
        
        async function loadVideosList() {
            try {
                const res = await fetch('/list_videos');
                const data = await res.json();
                if(data.videos) {
                    const sel = document.getElementById('video-selector');
                    sel.innerHTML = '';
                    data.videos.forEach(v => {
                        const opt = document.createElement('option');
                        opt.value = v;
                        opt.innerText = v;
                        if(v === videoName) opt.selected = true;
                        sel.appendChild(opt);
                    });
                }
            } catch(e) {}
        }
        
        function changeVideo(newVideo) {
            // Lógica para cambiar video. Por ahora, alertar al usuario.
            alert("Has seleccionado: " + newVideo + ".\n\nPara generar clips de este nuevo video, necesitas usar el botón 'Generar Nuevos Clips' y especificarlo.");
        }
        
        // Agregar CSS Animation para el loading
        const style = document.createElement('style');
        style.innerHTML = `@keyframes pulse { 0% { opacity: 1; transform: scale(1); } 50% { opacity: 0.5; transform: scale(1.05); } 100% { opacity: 1; transform: scale(1); } }`;
        document.head.appendChild(style);
        
        // Init
        loadVideosList();
    