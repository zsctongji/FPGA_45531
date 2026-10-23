@echo off
setlocal
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0tools\run_efinity.ps1" -Project camera_motion -Flow compile
if errorlevel 1 exit /b 1
exit /b 0
