@echo off
setlocal
cd /d "%~dp0.."
if not exist build\c_interfaces mkdir build\c_interfaces
call "C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat" >nul
if errorlevel 1 exit /b 1
set "task_src=projects\03_tinyml\embedded_sw\sapphire_soc_tinyml\software\standalone\tinyml_pdti8\src"
cl /nologo /EHsc /std:c++14 /I"%task_src%" /I"%task_src%\tensorflow\third_party\flatbuffers\include" team_work\03_ai_soc\tests\inspect_model.cpp "%task_src%\model\mobilenetv1_person_detect_model_data.cc" /Fobuild\c_interfaces\ /Febuild\c_interfaces\inspect_model.exe
if errorlevel 1 exit /b 1
build\c_interfaces\inspect_model.exe > logs\c1_model_structure.json
exit /b %errorlevel%

