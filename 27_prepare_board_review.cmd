@echo off
setlocal
cd /d "%~dp0"
echo Offline configuration generation and layout review. No board programming.
python -X utf8 tools\audit_soc_physical.py
if errorlevel 1 exit /b 1
powershell -NoProfile -ExecutionPolicy Bypass -File tools\run_soc_physical.ps1 -Flows pgm
if errorlevel 1 exit /b 1
python -X utf8 tools\check_board_preflight.py
if errorlevel 1 exit /b 1
echo PASS review artifacts. Hardware calibration and cold boot remain unverified.
exit /b 0
