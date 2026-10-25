@echo off
setlocal
cd /d "%~dp0"
python -X utf8 tools\run_c2_selftest.py
if errorlevel 1 exit /b 1
python -X utf8 tools\check_a_c2_pc.py --video-capture
exit /b %errorlevel%
