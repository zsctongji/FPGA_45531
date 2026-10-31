@echo off
cd /d "%~dp0"
echo Offline audits only. No board, GPIO, UART or JTAG access.
echo Requires current native map, 53-run C2 regression and pinned A/B archives.
python -X utf8 tools\audit_pin_ownership.py
if errorlevel 1 exit /b 1
python -X utf8 tools\audit_bram_usage.py
if errorlevel 1 exit /b 1
echo PASS offline audits. Physical pin/clock/voltage/PNR readiness remains REVIEW_REQUIRED.
exit /b 0
