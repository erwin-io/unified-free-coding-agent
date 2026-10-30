@echo off
setlocal
cd /d "%~dp0"
title Unified Agent - Tech Lead Review Packet
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0run.ps1" -Mode review
set "RC=%ERRORLEVEL%"
echo Press any key to close.
pause >nul
exit /b %RC%
