@echo off
setlocal
cd /d "%~dp0.."
if not exist build\c3 mkdir build\c3
call "C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat" >nul
if errorlevel 1 exit /b 1
cl /nologo /std:c11 /W4 /WX /TC /Iteam_work\shared\include /Iteam_work\03_ai_soc\c2 /Iteam_work\03_ai_soc\c3_hal team_work\shared\src\cooperation_v1.c team_work\03_ai_soc\c3_hal\c3_hal.c team_work\03_ai_soc\c3_hal\c3_shared_time.c team_work\03_ai_soc\c3_hal\c3_peripheral.c team_work\03_ai_soc\c3_hal\c3_thermal_publish.c team_work\03_ai_soc\tests\test_c3_peripheral.c /Fobuild\c3\ /Febuild\c3\test_c3_peripheral.exe
if errorlevel 1 exit /b 1
build\c3\test_c3_peripheral.exe
exit /b %errorlevel%
