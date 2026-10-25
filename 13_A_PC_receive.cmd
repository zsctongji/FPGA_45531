@echo off
setlocal
set "PYTHONHOME=%~dp0tools\efinity\2026.1\python311"
cd /d "%~dp0"
echo Listening for board UDP on port 39003. Dashboard http://127.0.0.1:39004
echo No firewall or adapter settings are changed. Ctrl+C stops recording.
"tools\efinity\2026.1\python311\bin\python.exe" -X utf8 "tools\a_side\receiver.py" --bind 0.0.0.0 --output "logs\a_side\received"
pause
