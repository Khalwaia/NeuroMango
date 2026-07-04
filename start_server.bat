@echo off
title NeuroMango Server
echo Starting NeuroMango Server...
echo Loading AI Models (XTTS and ChromaDB) - This will take about 1-2 minutes!
echo.
call venv\Scripts\activate.bat
echo Launching Voice ASR Client...
start "NeuroMango Voice ASR" cmd /k "venv\Scripts\activate.bat && python chat_client.py"
python -u server.py
pause
