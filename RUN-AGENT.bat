@echo off
setlocal
cd /d "%~dp0"
title Unified Free Coding Agent
echo Unified Free Coding Agent - uses PROJECT_PATH in .env
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0run.ps1" -Mode start
set "RC=%ERRORLEVEL%"
if not "%RC%"=="0" echo Launcher exited with error code %RC%.
echo Press any key to close this window.
pause >nul
exit /b %RC%
