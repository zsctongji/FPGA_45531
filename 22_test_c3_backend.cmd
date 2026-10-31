@echo off
setlocal
cd /d "%~dp0"
python -X utf8 tools\check_c3_backend.py
exit /b %errorlevel%
