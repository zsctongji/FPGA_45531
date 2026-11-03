@echo off
setlocal
cd /d "%~dp0"
python tools\run_c2_selftest.py
set "C2_EXIT=%ERRORLEVEL%"
echo.
echo C2 functional simulation only. See logs\c2_selftest.json.
pause
exit /b %C2_EXIT%
