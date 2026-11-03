@echo off
setlocal
cd /d "%~dp0"
echo Standalone destructive DDR diagnosis. Offline build only; no board access.
python -X utf8 tools\prepare_ddr_diag.py
if errorlevel 1 exit /b 1
python -X utf8 tools\check_ddr_diag.py --sim-only
if errorlevel 1 exit /b 1
powershell -NoProfile -ExecutionPolicy Bypass -File tools\run_ddr_diag.ps1
if errorlevel 1 exit /b 1
python -X utf8 tools\check_ddr_diag.py
if errorlevel 1 exit /b 1
echo PASS offline diagnostic image. Hardware calibration and memory test remain unverified.
exit /b 0
