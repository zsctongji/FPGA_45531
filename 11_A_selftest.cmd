@echo off
setlocal
set "PYTHONHOME=%~dp0tools\efinity\2026.1\python311"
cd /d "%~dp0"
"tools\efinity\2026.1\python311\bin\python.exe" -X utf8 "tools\run_a_side.py"
set "A_RESULT=%ERRORLEVEL%"
echo A tests exit code: %A_RESULT%. Details: logs\a_side_selftest.json
pause
exit /b %A_RESULT%
