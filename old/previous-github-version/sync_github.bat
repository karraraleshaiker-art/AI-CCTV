@echo off
setlocal
title AI-CCTV Sync - Al Noor Solar Factory
cd /d "%~dp0"

set "GIT_BASH=%ProgramFiles%\Git\bin\bash.exe"
if not exist "%GIT_BASH%" set "GIT_BASH=%ProgramFiles%\Git\usr\bin\bash.exe"
if not exist "%GIT_BASH%" set "GIT_BASH=%ProgramFiles(x86)%\Git\bin\bash.exe"

if not exist "%GIT_BASH%" (
  echo ERROR: Git Bash was not found.
  echo Install Git for Windows, then run this file again.
  pause
  exit /b 1
)

"%GIT_BASH%" "./sync_github.sh" %*
set "EXIT_CODE=%ERRORLEVEL%"

echo.
if not "%EXIT_CODE%"=="0" (
  echo Sync script failed with exit code %EXIT_CODE%.
)
pause
exit /b %EXIT_CODE%
