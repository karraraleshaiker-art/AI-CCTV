@echo off
setlocal EnableDelayedExpansion
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

where git >nul 2>nul
if errorlevel 1 (
  echo Git was not found. Install Git, then run this file again.
  pause
  exit /b 1
)

echo.
echo Collecting sanitized diagnostics...
for /f "usebackq delims=" %%P in (`"%PYTHON_EXE%" -m tools.collect_diagnostics`) do set "ZIP_PATH=%%P"

if not exist "!ZIP_PATH!" (
  echo Could not find diagnostics zip:
  echo !ZIP_PATH!
  pause
  exit /b 1
)

echo Diagnostics zip:
echo !ZIP_PATH!
echo.
echo Syncing with GitHub...

git config user.name >nul 2>nul
if errorlevel 1 git config user.name "AI CCTV Diagnostics"
git config user.email >nul 2>nul
if errorlevel 1 git config user.email "ai-cctv-diagnostics@local"

git pull --rebase origin main
if errorlevel 1 (
  echo Git pull failed. Fix the message above, then run this file again.
  pause
  exit /b 1
)

git add -f "!ZIP_PATH!"
git commit -m "Add AI CCTV diagnostics"
if errorlevel 1 (
  echo Nothing was committed. The diagnostics zip may already be uploaded.
  pause
  exit /b 1
)

git push origin main
if errorlevel 1 (
  echo Git push failed. Check GitHub login/network access, then run this file again.
  pause
  exit /b 1
)

echo.
echo Diagnostics uploaded to GitHub.
echo You can now tell Codex to read the latest diagnostics zip.
pause
