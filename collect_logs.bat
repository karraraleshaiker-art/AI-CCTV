@echo off
setlocal
cd /d "%~dp0"

set "PYTHON_EXE="
if exist ".venv\Scripts\python.exe" set "PYTHON_EXE=.venv\Scripts\python.exe"
if "%PYTHON_EXE%"=="" (
  where python >nul 2>nul
  if not errorlevel 1 set "PYTHON_EXE=python"
)
if "%PYTHON_EXE%"=="" (
  where py >nul 2>nul
  if not errorlevel 1 set "PYTHON_EXE=py"
)

if "%PYTHON_EXE%"=="" (
  echo Python was not found.
  pause
  exit /b 1
)

for /f "usebackq delims=" %%P in (`"%PYTHON_EXE%" -m tools.collect_diagnostics`) do set "ZIP_PATH=%%P"

echo.
echo Diagnostics package created:
echo %ZIP_PATH%
echo.
echo This package does not include config.local.json or the NVR password.
pause
