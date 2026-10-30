@echo off
setlocal
cd /d "%~dp0"
title Unified Agent - Connect GitHub CLI
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\github-access.ps1" -Action connect
set "RC=%ERRORLEVEL%"
echo Press any key to close.
pause >nul
exit /b %RC%
