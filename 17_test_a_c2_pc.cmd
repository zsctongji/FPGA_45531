@echo off
setlocal
cd /d "%~dp0"
python tools\run_c2_selftest.py
if errorlevel 1 goto failed
python tools\check_a_c2_pc.py
if errorlevel 1 goto failed
echo PASS A/C2 RTL and desktop inference checks. Firmware build: 16_build_c24.cmd
pause
exit /b 0
:failed
echo FAILED. See logs\c2_selftest.json and logs\a_c2_pc_inference.json.
pause
exit /b 1
