with open('pipeline.py', 'r', encoding='utf-8') as f:
    text = f.read()

target1 = "'social_title' (string, Título muy gracioso para TikTok/IG en español argentino), 'social_desc' (string, descripción CORTA y directa en PRIMERA PERSONA, {link_instruction} usa SOLO hashtags genéricos, súper populares del juego y de gaming, PROHIBIDO INVENTAR hashtags sobre nombres de amigos o chistes internos (ej: PROHIBIDO #KEVINELMUTANTE), usa solo tags de millones de vistas), 'yt_title'"
replacement1 = "'social_title' (string, Título ingenioso y directo que resuma EXACTAMENTE lo que pasa o se dice en el clip), 'social_desc' (string, descripción MUY CORTA de APENAS UN RENGLÓN (máximo 10 palabras) que tenga sentido con el clip, en PRIMERA PERSONA. {link_instruction} Luego pon solo 3 hashtags populares del juego), 'yt_title'"

target2 = "\\\"social_title\\\": \\\"Título muy gracioso y viral para TikTok/IG en español argentino auténtico\\\", \\\"social_desc\\\": \\\"Descripción CORTA y directa para TikTok/IG en PRIMERA PERSONA, {link_instruction} usa SOLO hashtags genéricos, súper populares del juego y de gaming, PROHIBIDO INVENTAR hashtags sobre nombres de amigos o chistes internos (ej: PROHIBIDO #KEVINELMUTANTE), usa solo tags de millones de vistas\\\", \\\"yt_title\\\""
replacement2 = "\\\"social_title\\\": \\\"Título ingenioso y directo que resuma EXACTAMENTE lo que pasa o se dice en el clip\\\", \\\"social_desc\\\": \\\"Descripción MUY CORTA de APENAS UN RENGLÓN (máx 10 palabras) que tenga sentido con el clip, en PRIMERA PERSONA. {link_instruction} Luego pon solo 3 hashtags populares del juego\\\", \\\"yt_title\\\""

if target1 in text:
    text = text.replace(target1, replacement1)
else:
    print("Target 1 not found")
if target2 in text:
    text = text.replace(target2, replacement2)
else:
    print("Target 2 not found")

with open('pipeline.py', 'w', encoding='utf-8') as f:
    f.write(text)
print("Done")
