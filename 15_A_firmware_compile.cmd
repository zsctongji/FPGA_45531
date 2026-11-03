@echo off
setlocal
set "PYTHONHOME=%~dp0tools\efinity\2026.1\python311"
cd /d "%~dp0"
"tools\efinity\2026.1\python311\bin\python.exe" -X utf8 "tools\build_a_firmware.py"
set "A_RESULT=%ERRORLEVEL%"
pause
exit /b %A_RESULT%
