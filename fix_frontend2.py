with open('templates/index.html', 'r', encoding='utf-8') as f:
    text = f.read()

import re
text = re.sub(r'// Polling al backend cada 500ms.*?\n\s*\}\);', 
'''const res = await fetchPromise;
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
                                progressText.innerText = progJson.percent + "% - " + progJson.message;
                            } else if (progJson.status === "idle") {
                                clearInterval(checkInterval);
                                resolve();
                            } else if (progJson.status === "error") {
                                clearInterval(checkInterval);
                                reject(new Error(progJson.message));
                            }
                        } catch(e) {}
                    }, 1000);
                });''', text, flags=re.DOTALL)

with open('templates/index.html', 'w', encoding='utf-8') as f:
    f.write(text)
print("index.html fully replaced")
