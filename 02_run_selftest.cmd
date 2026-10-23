@echo off
setlocal
pushd "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0tools\run_selftest.ps1"
set "TASK_EXIT=%ERRORLEVEL%"
popd
if not "%FPGA_NO_PAUSE%"=="1" pause
exit /b %TASK_EXIT%
