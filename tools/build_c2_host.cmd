@echo off
setlocal
cd /d "%~dp0.."
if not exist build\c2 mkdir build\c2
call "C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat" >nul
if errorlevel 1 exit /b 1
cl /nologo /std:c11 /W4 /WX /TC /Iteam_work\shared\include /Iteam_work\03_ai_soc\c2 /Iteam_work\03_ai_soc\c4 /Iteam_work\03_ai_soc\c24 team_work\shared\src\cooperation_v1.c team_work\03_ai_soc\c2\c2_driver.c team_work\03_ai_soc\c4\c4_bridge.c team_work\03_ai_soc\c24\c24_pipeline.c team_work\03_ai_soc\tests\test_c2_driver.c /Fobuild\c2\ /Febuild\c2\test_c2_driver.exe
if errorlevel 1 exit /b 1
build\c2\test_c2_driver.exe
if errorlevel 1 exit /b 1
cl /nologo /std:c11 /W4 /WX /TC /Iteam_work\shared\include /Iteam_work\03_ai_soc\c2 /Iteam_work\03_ai_soc\c3_hal team_work\03_ai_soc\c3_hal\c3_shared_time.c team_work\03_ai_soc\tests\test_c3_shared_time.c /Fobuild\c2\ /Febuild\c2\test_c3_shared_time.exe
if errorlevel 1 exit /b 1
build\c2\test_c3_shared_time.exe
exit /b %errorlevel%
