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
".venv\Scripts\python.exe" -c "import cv2, numpy" >nul 2>nul
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

echo.
echo Testing NVR RTSP connection.
echo Default NVR: 192.168.100.203, channel 14, main stream.
echo Enter the NVR password when asked. It will not be saved.
echo.

".venv\Scripts\python.exe" tools\rtsp_probe.py --host 192.168.100.203 --channel 14 --stream main --template hikvision --username admin

echo.
pause
