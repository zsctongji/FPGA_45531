@echo off
setlocal
set "PYTHONHOME=%~dp0tools\efinity\2026.1\python311"
cd /d "%~dp0"
echo SYNTHETIC LOCALHOST DEMO. This is NOT real board evidence.
echo Open http://127.0.0.1:39004 after the receiver starts. Ctrl+C stops it.
"tools\efinity\2026.1\python311\bin\python.exe" -X utf8 "tools\a_side\demo.py" --output "logs\a_side\pc_demo"
pause
