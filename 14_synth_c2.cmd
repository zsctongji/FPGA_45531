@echo off
setlocal
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File tools\run_c2_synthesis.ps1
set "C2_EXIT=%ERRORLEVEL%"
echo.
echo C2 boundary synthesis only. No board programming file is generated.
pause
exit /b %C2_EXIT%
