@echo off
cd /d "%~dp0"
echo A-only synthesis. No programming file or board download.
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "tools\run_a_synthesis.ps1"
set "A_RESULT=%ERRORLEVEL%"
pause
exit /b %A_RESULT%
