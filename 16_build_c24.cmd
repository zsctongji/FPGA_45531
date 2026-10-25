@echo off
setlocal
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File tools\build_c24.ps1
set "C24_EXIT=%ERRORLEVEL%"
echo.
echo C24 firmware build only. Synthetic self-test; live C2 MMIO is disabled.
pause
exit /b %C24_EXIT%
