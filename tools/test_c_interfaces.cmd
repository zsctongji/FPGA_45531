@echo off
setlocal
cd /d "%~dp0.."
if not exist build\c_interfaces mkdir build\c_interfaces
call "C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat" >nul
if errorlevel 1 exit /b 1
cl /nologo /std:c11 /W4 /WX /TC /Iteam_work\shared\include /Iteam_work\03_ai_soc\c3_hal team_work\shared\src\cooperation_v1.c team_work\03_ai_soc\c3_hal\c3_hal.c team_work\03_ai_soc\tests\test_interfaces.c /Fobuild\c_interfaces\ /Febuild\c_interfaces\test_interfaces.exe
if errorlevel 1 exit /b 1
build\c_interfaces\test_interfaces.exe
if errorlevel 1 exit /b 1
python team_work\03_ai_soc\tests\test_c1_parser.py
exit /b %errorlevel%

