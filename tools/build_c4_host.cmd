@echo off
setlocal
cd /d "%~dp0.."
if not exist build\c4 mkdir build\c4
call "C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat" >nul
if errorlevel 1 exit /b 1
set "task_inc=/Iteam_work\shared\include /Iteam_work\03_ai_soc\c4 /Iteam_work\03_ai_soc\c3_hal"
cl /nologo /std:c11 /W4 /WX /TC %task_inc% team_work\shared\src\cooperation_v1.c team_work\03_ai_soc\c4\c4_bridge.c team_work\03_ai_soc\c3_hal\c3_hal.c team_work\03_ai_soc\c3_hal\c3_replay.c team_work\03_ai_soc\tests\test_c4.c /Fobuild\c4\ /Febuild\c4\test_c4.exe
if errorlevel 1 exit /b 1
build\c4\test_c4.exe
if errorlevel 1 exit /b 1
cl /nologo /std:c11 /W4 /WX /TC /LD %task_inc% team_work\shared\src\cooperation_v1.c team_work\03_ai_soc\c4\c4_bridge.c /Fobuild\c4\ /Febuild\c4\c4_bridge.dll
exit /b %errorlevel%

