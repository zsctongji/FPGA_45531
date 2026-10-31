@echo off
setlocal
cd /d "%~dp0"
python -X utf8 tools\replay_team_real_data.py
exit /b %errorlevel%
