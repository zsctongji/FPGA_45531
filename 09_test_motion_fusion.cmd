@echo off
setlocal
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0tools\run_selftest.ps1" -Suite events
if errorlevel 1 exit /b 1
exit /b 0
