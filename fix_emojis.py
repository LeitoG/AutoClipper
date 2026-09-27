import re

with open(r'c:\Users\leone\Desktop\OBS Grabaciones\Exports\Complete Games\templates\index.html', 'r', encoding='utf-8') as f:
    text = f.read()

# The corruption is deep, I'll just regex replace the specific text blocks
text = re.sub(r'<i>.*?</i>Encuadre', '<i>📸</i>Encuadre', text)
text = re.sub(r'<i>.*?</i>Subt.*?tulos', '<i>📝</i>Subtítulos', text)
text = re.sub(r'<i>.*?</i>Gancho', '<i>🪝</i>Gancho', text)
text = re.sub(r'<i>.*?</i>Stickers', '<i>🤡</i>Stickers', text)
text = re.sub(r'<i>.*?</i>Redes', '<i>📱</i>Redes', text)
text = re.sub(r'<i>.*?</i>Final Img', '<i>🎬</i>Final Img', text)
text = re.sub(r'<i>.*?</i>Audio', '<i>🎚️</i>Audio', text)
text = re.sub(r'<i>.*?</i>Volver', '<i>🔙</i>Volver', text)

text = re.sub(r'Configuraci.*?n de Directorios', 'Configuración de Directorios', text)
text = re.sub(r'>.*? Config<', '>⚙️ Config<', text)
text = re.sub(r'>.*? Historial y Redes<', '>🕒 Historial y Redes<', text)
text = re.sub(r'>.*? Guardar y Reiniciar<', '>💾 Guardar y Reiniciar<', text)
text = re.sub(r'>.*? Subir Logo<', '>📸 Subir Logo<', text)
text = re.sub(r'>.*? Guardar Global<', '>💾 Guardar Global<', text)
text = re.sub(r'Configuraci.*?n guardada exitosamente\. La p.*?gina se recargar.*?\.', 'Configuración guardada exitosamente. La página se recargará.', text)
text = re.sub(r'Error al guardar la configuraci.*?n\.', 'Error al guardar la configuración.', text)
text = re.sub(r'Listado de Videos', '📋 Listado de Videos', text)
text = re.sub(r'Calendario de Publicaci.*?n', '📅 Calendario de Publicación', text)
text = re.sub(r'Aprobar y.*?Guardar', '✅ Aprobar y<br>Guardar', text)
text = re.sub(r'Exportar a.*?FFmpeg', '🚀 Exportar a<br>FFmpeg', text)
text = re.sub(r'Generar Nuevos Clips.*?con IA', '✨ Generar Nuevos Clips<br>con IA', text)
text = re.sub(r'Clip Manual', '✂️<br>Clip Manual', text)
text = re.sub(r'Unir Clips Seleccionados', '🔗 Unir Clips Seleccionados', text)
text = re.sub(r'Deshacer', '↩️<br>Deshacer', text)
text = re.sub(r'Rehacer', '↪️<br>Rehacer', text)
text = re.sub(r'Eliminar.*?Escena', '🗑️<br>Eliminar<br>Escena', text)
text = re.sub(r'Duplicar.*?Escena', '📑<br>Duplicar<br>Escena', text)
text = re.sub(r'Cortar.*?Escena', '✂️<br>Cortar<br>Escena', text)
text = re.sub(r'Rebobinar', '⏱️ Rebobinar', text)
text = re.sub(r'Gasto Estimado', '💸 Gasto Estimado', text)
text = re.sub(r'Duraci.*?n:', 'Duración:', text)
text = re.sub(r'C.*?mara', 'Cámara', text)
text = re.sub(r'Audio.*?Activado', '🔊 Audio<br>Activado', text)
text = re.sub(r'Audio.*?Desactivado', '🔇 Audio<br>Desactivado', text)

with open(r'c:\Users\leone\Desktop\OBS Grabaciones\Exports\Complete Games\templates\index.html', 'w', encoding='utf-8') as f:
    f.write(text)

print("Done")
