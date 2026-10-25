@echo off
setlocal
cd /d "%~dp0"
python tools\run_c2_selftest.py
if errorlevel 1 exit /b 1
python tools\test_c24_acceptance.py
exit /b %errorlevel%
