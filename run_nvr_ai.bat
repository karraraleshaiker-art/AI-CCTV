@echo off
setlocal
cd /d "%~dp0"

where py >nul 2>nul
set "HAS_PY=%ERRORLEVEL%"
where python >nul 2>nul
set "HAS_PYTHON=%ERRORLEVEL%"

if "%HAS_PY%" NEQ "0" if "%HAS_PYTHON%" NEQ "0" (
  echo.
  echo Python was not found. Install Python 3.11 or 3.12, then run this file again.
  echo.
  pause
  exit /b 1
)

echo.
echo AI CCTV NVR Launcher
echo ====================
echo This will check Python requirements, then ask for your NVR login.
echo Default NVR: 192.168.100.203, channel 14, main stream.
echo Keep this window open while the camera AI is running.
echo Press CTRL+C in this window to stop the system.
echo A log will be written to runtime_launcher.log
echo.

if not exist ".venv\Scripts\python.exe" (
  echo Creating local Python environment...
  if "%HAS_PY%"=="0" py -3.12 -m venv .venv
  if not exist ".venv\Scripts\python.exe" if "%HAS_PY%"=="0" py -3.11 -m venv .venv
  if not exist ".venv\Scripts\python.exe" if "%HAS_PYTHON%"=="0" python -m venv .venv
  if not exist ".venv\Scripts\python.exe" (
    echo Could not create .venv.
    pause
    exit /b 1
  )
)

echo Checking Python packages...
".venv\Scripts\python.exe" -c "import fastapi, uvicorn, cv2, ultralytics, numpy" >nul 2>nul
if errorlevel 1 (
  echo Installing requirements...
  ".venv\Scripts\python.exe" -m pip install --upgrade pip
  ".venv\Scripts\python.exe" -m pip install -r requirements.txt
  if errorlevel 1 (
    echo Could not install requirements. Check internet connection or Python version.
    pause
    exit /b 1
  )
)

".venv\Scripts\python.exe" -u -m tools.run_nvr

echo.
echo System stopped.
pause
