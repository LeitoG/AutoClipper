with open('templates/index.html', 'r', encoding='utf-8') as f:
    text = f.read()

target = '''                // Esperar a que el backend termine
                const res = await fetchPromise;
                clearInterval(progressInterval);
                const json = await res.json();
                
                if(json.status === "error") throw new Error(json.message);
                
                progressBar.style.width = '100%';
                progressText.innerText = "Clips generados exitosamente!";
                
                // Actualizar costos
                fetchCosts();
                
                // Recargar toda la UI con los nuevos clips
                setTimeout(async () => {
                    loadingScreen.classList.add('hidden');
                    await init();
                    await enforceNoOverlaps();
                }, 800);
                
            } catch (err) {
                alert(" Error de IA: " + err.message);
                loadingScreen.classList.add('hidden');
            }'''

replacement = '''                const res = await fetchPromise;
                const json = await res.json();
                if(json.status === "error") {
                    clearInterval(progressInterval);
                    throw new Error(json.message);
                }

                // Esperar a que el backend termine haciendo polling al estado
                await new Promise((resolve, reject) => {
                    const checkInterval = setInterval(async () => {
                        try {
                            const progRes = await fetch('/progress');
                            const progJson = await progRes.json();
                            if (progJson.status === "idle" && progJson.percent === 100) {
                                clearInterval(checkInterval);
                                clearInterval(progressInterval);
                                resolve();
                            } else if (progJson.status === "error") {
                                clearInterval(checkInterval);
                                clearInterval(progressInterval);
                                reject(new Error(progJson.message));
                            }
                        } catch(e) {}
                    }, 1000);
                });
                
                progressBar.style.width = '100%';
                progressText.innerText = "Clips generados exitosamente!";
                
                // Actualizar costos
                fetchCosts();
                
                // Recargar toda la UI con los nuevos clips
                setTimeout(async () => {
                    loadingScreen.classList.add('hidden');
                    await init();
                    await enforceNoOverlaps();
                }, 800);
                
            } catch (err) {
                alert(" Error de IA: " + err.message);
                loadingScreen.classList.add('hidden');
            }'''

text = text.replace(target, replacement)

# Wait, in the target above I replaced progressInterval but in the index.html, progressInterval is defined outside this block. Let's make sure I'm not duplicating interval clearing.
# I will actually remove the original progressInterval entirely and just use one polling interval.

target2 = '''                // Polling al backend cada 500ms
                const progressInterval = setInterval(async () => {
                    try {
                        const progRes = await fetch('/progress');
                        const progJson = await progRes.json();
                        if (progJson.status === "processing") {
                            progressBar.style.width = progJson.percent + '%';
                            progressText.innerText = ${progJson.percent}% - ;
                        }
                    } catch(e) {}
                }, 500);
                
                const res = await fetchPromise;
                const json = await res.json();
                if(json.status === "error") {
                    clearInterval(progressInterval);
                    throw new Error(json.message);
                }

                // Esperar a que el backend termine haciendo polling al estado
                await new Promise((resolve, reject) => {
                    const checkInterval = setInterval(async () => {
                        try {
                            const progRes = await fetch('/progress');
                            const progJson = await progRes.json();
                            if (progJson.status === "idle" && progJson.percent === 100) {
                                clearInterval(checkInterval);
                                clearInterval(progressInterval);
                                resolve();
                            } else if (progJson.status === "error") {
                                clearInterval(checkInterval);
                                clearInterval(progressInterval);
                                reject(new Error(progJson.message));
                            }
                        } catch(e) {}
                    }, 1000);
                });'''

replacement2 = '''                const res = await fetchPromise;
                const json = await res.json();
                if(json.status === "error") {
                    throw new Error(json.message);
                }

                // Polling al backend hasta que termine
                await new Promise((resolve, reject) => {
                    const checkInterval = setInterval(async () => {
                        try {
                            const progRes = await fetch('/progress');
                            const progJson = await progRes.json();
                            if (progJson.status === "processing") {
                                progressBar.style.width = progJson.percent + '%';
                                progressText.innerText = ${progJson.percent}% - ;
                            } else if (progJson.status === "idle") {
                                clearInterval(checkInterval);
                                resolve();
                            } else if (progJson.status === "error") {
                                clearInterval(checkInterval);
                                reject(new Error(progJson.message));
                            }
                        } catch(e) {}
                    }, 1000);
                });'''

text = text.replace(target2, replacement2)

with open('templates/index.html', 'w', encoding='utf-8') as f:
    f.write(text)
print("index.html frontend polling refactored")
