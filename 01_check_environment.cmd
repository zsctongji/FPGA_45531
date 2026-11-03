@echo off
setlocal
chcp 65001 >nul
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0tools\check_environment.ps1" %*
set "FPGA_CHECK_EXIT=%ERRORLEVEL%"
echo.
echo Report: "%~dp0logs\environment.json"
if not "%FPGA_NO_PAUSE%"=="1" pause
exit /b %FPGA_CHECK_EXIT%
