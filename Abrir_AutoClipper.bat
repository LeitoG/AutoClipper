@echo off
echo Iniciando Servidor AutoClipper...
start cmd /k "uvicorn backend:app --host 0.0.0.0 --port 8000 --reload"
echo Esperando a que el servidor inicie...
timeout /t 4 /nobreak > nul
start http://localhost:8000
exit
