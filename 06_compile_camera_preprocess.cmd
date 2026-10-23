@echo off
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0tools\run_efinity.ps1" -Project camera_preprocess -Flow compile
set "FPGA_RUN_RESULT=%errorlevel%"
if not defined FPGA_NO_PAUSE pause
exit /b %FPGA_RUN_RESULT%
