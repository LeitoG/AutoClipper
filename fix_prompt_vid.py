import re

with open('pipeline.py', 'r', encoding='utf-8') as f:
    text = f.read()

target = r"Recibes el AUDIO EXACTO y la transcripcion de una seccion de \{CHUNK_DUR/60\} minutos\. Usa el AUDIO para distinguir cuando estas leyendo dialogos del juego de cuando estas reaccionando espontaneamente, hablando a tu chat o gritando de un susto\. PRIORIZA LAS REACCIONES REALES, CHISTES Y SUSTOS\."

replacement = r'''Recibes el VIDEO EXACTO (a 1 frame por segundo) y la transcripcion de una seccion de {CHUNK_DUR/60} minutos. Usa el VIDEO y el AUDIO para entender el contexto visual (ej: si murio en el juego, si hay un boss, sus expresiones faciales) y distinguir cuando esta leyendo dialogos del juego de cuando reacciona espontaneamente. PRIORIZA LAS REACCIONES REALES, CHISTES, SUSTOS Y MUERTES EPICAS.'''

new_text = re.sub(target, replacement, text)
if new_text != text:
    with open('pipeline.py', 'w', encoding='utf-8') as f:
        f.write(new_text)
    print("Replaced prompt!")
else:
    print("Not replaced prompt.")
