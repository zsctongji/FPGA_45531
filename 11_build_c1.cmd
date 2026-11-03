@echo off
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0tools\build_c1.ps1"
set "task_exit=%errorlevel%"
pause
exit /b %task_exit%

