@echo off
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0tools\build_person_detect.ps1"
set "FPGA_RUN_RESULT=%errorlevel%"
if not defined FPGA_NO_PAUSE pause
exit /b %FPGA_RUN_RESULT%
