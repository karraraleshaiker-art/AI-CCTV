@echo off
setlocal
title AI CCTV - Python Environment Setup
cd /d "%~dp0"

echo ==========================================
echo    AI CCTV Python Environment Setup
echo ==========================================
echo.

where py >nul 2>nul
if errorlevel 1 (
  echo ERROR: Python Launcher was not found.
  echo Install Python 3.12, then run this file again.
  pause
  exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
  echo Creating .venv with Python 3.12...
  py -3.12 -m venv .venv
  if errorlevel 1 (
    echo ERROR: Could not create .venv with Python 3.12.
    echo Check that Python 3.12 is installed.
    pause
    exit /b 1
  )
) else (
  echo Existing .venv found.
)

echo Upgrading pip...
".venv\Scripts\python.exe" -m pip install --upgrade pip
if errorlevel 1 (
  echo ERROR: pip upgrade failed.
  pause
  exit /b 1
)

echo.
echo Choose environment type:
echo   1. Stable Core only (main.py)
echo   2. Full Web Platform (app.py + database + face engine)
echo.
set /p choice="Enter 1 or 2: "

if "%choice%"=="2" (
  echo Installing full web platform dependencies...
  ".venv\Scripts\python.exe" -m pip install -r requirements-web.txt
) else (
  echo Installing stable core dependencies...
  ".venv\Scripts\python.exe" -m pip install -r requirements-stable.txt
)

if errorlevel 1 (
  echo ERROR: Dependency installation failed.
  pause
  exit /b 1
)

echo.
echo Environment setup complete.
echo You can now run run_ai_cctv.bat.
pause
