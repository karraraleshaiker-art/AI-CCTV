@echo off
setlocal
title AI CCTV Launcher - Al Noor Solar Factory
cd /d "%~dp0"
echo ==========================================
echo    AI CCTV Launcher
echo    Al Noor Factory for Solar Panels
echo ==========================================
echo.

if not exist ".venv\Scripts\python.exe" (
  echo ERROR: .venv was not found.
  echo Run setup_venv.bat first.
  pause
  exit /b 1
)

echo Choose what to run:
echo   1. Stable Core - original OpenCV window (main.py)
echo   2. Web Platform - FastAPI dashboard (app.py)
echo.
set /p choice="Enter 1 or 2: "

if "%choice%"=="2" (
  call run_web_platform.bat
) else (
  call run_stable_core.bat
)
