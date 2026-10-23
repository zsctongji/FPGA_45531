@echo off
setlocal
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0tools\run_efinity.ps1" -Project tinyml -Flow compile
set "TASK_EXIT=%ERRORLEVEL%"
if not "%FPGA_NO_PAUSE%"=="1" pause
exit /b %TASK_EXIT%
