@echo off
setlocal
cd /d "%~dp0"

set "STAMP=%DATE:/=-%_%TIME::=-%"
set "STAMP=%STAMP: =_%"
set "DIAG_DIR=diagnostics\ai-cctv-diagnostics-%STAMP%"
set "ZIP_PATH=%DIAG_DIR%.zip"

mkdir "%DIAG_DIR%" >nul 2>nul

if exist runtime_launcher.log copy runtime_launcher.log "%DIAG_DIR%\" >nul
if exist runtime_logs xcopy runtime_logs "%DIAG_DIR%\runtime_logs\" /E /I /Y >nul
if exist config.example.json copy config.example.json "%DIAG_DIR%\" >nul
if exist config.nvr.example.json copy config.nvr.example.json "%DIAG_DIR%\" >nul
if exist runtime_state.json copy runtime_state.json "%DIAG_DIR%\" >nul

powershell -NoProfile -ExecutionPolicy Bypass -Command "Compress-Archive -Path '%DIAG_DIR%\*' -DestinationPath '%ZIP_PATH%' -Force"

echo.
echo Diagnostics package created:
echo %CD%\%ZIP_PATH%
echo.
echo This package does not include config.local.json or the NVR password.
pause
