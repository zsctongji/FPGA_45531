@echo off
setlocal
cd /d "%~dp0"
echo V4 reference offline build. No programming, UART, JTAG or GPIO access.
python -X utf8 tools\prepare_soc_physical.py --cpu-mhz 100
if errorlevel 1 exit /b 1
python -X utf8 tools\test_c7_cpu_lanes.py
if errorlevel 1 exit /b 1
python -X utf8 tools\check_soc_physical.py
if errorlevel 1 exit /b 1
python -X utf8 tools\test_physical_c2.py
if errorlevel 1 exit /b 1
powershell -NoProfile -ExecutionPolicy Bypass -File tools\run_soc_physical.ps1
if errorlevel 1 exit /b 1
powershell -NoProfile -ExecutionPolicy Bypass -File tools\run_soc_physical.ps1 -Flows sta_tclsh
if errorlevel 1 exit /b 1
python -X utf8 tools\audit_soc_physical.py
if errorlevel 1 exit /b 1
python -X utf8 tools\export_physical_evidence.py
if errorlevel 1 exit /b 1
echo PASS offline implementation and reference audit. Physical release remains disabled.
exit /b 0
