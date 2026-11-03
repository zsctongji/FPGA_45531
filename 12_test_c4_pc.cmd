@echo off
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0tools\run_c4_pc_checks.ps1"
set "task_exit=%errorlevel%"
pause
exit /b %task_exit%

