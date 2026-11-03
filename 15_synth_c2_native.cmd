@echo off
setlocal
cd /d "%~dp0"
python tools\prepare_c2_vendor.py
if errorlevel 1 exit /b 1
powershell -NoProfile -ExecutionPolicy Bypass -File tools\run_c2_synthesis.ps1 -Target native
set "C2_EXIT=%ERRORLEVEL%"
echo.
echo Native CPU/TinyML/DDR overlay synthesis only. Video input remains external.
echo This does not generate a board programming package.
pause
exit /b %C2_EXIT%
