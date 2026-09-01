@echo off
setlocal
title AI CCTV v0.4 - Stable Core
cd /d "%~dp0"

echo ==========================================
echo       AI CCTV v0.4 - STABLE CORE
echo ==========================================
echo.

if not exist ".venv\Scripts\python.exe" (
  echo ERROR: .venv was not found.
  echo Run setup_venv.bat first.
  pause
  exit /b 1
)

set "OPENCV_FFMPEG_CAPTURE_OPTIONS=rtsp_transport;tcp"
".venv\Scripts\python.exe" main.py

echo.
echo Application closed.
pause
