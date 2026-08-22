@echo off
setlocal
title AI CCTV Vision Platform - Al Noor Solar Factory
cd /d "%~dp0"
echo ==========================================
echo    AI CCTV Web Platform (FastAPI)
echo    Al Noor Factory for Solar Panels
echo ==========================================
echo.
if not exist ".venv\Scripts\python.exe" (
  echo ERROR: Existing .venv not found.
  echo Put these files in the SAME project folder that contains your working .venv.
  pause
  exit /b 1
)
set "OPENCV_FFMPEG_CAPTURE_OPTIONS=rtsp_transport;tcp"
echo Starting Logs Reader in background (port 8808)...
start "" /B ".venv\Scripts\python.exe" logs_reader.py
echo Starting AI CCTV Platform (port 8000)...
".venv\Scripts\python.exe" app.py
echo.
echo Application closed.
pause
