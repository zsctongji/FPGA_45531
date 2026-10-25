@echo off
setlocal
cd /d "%~dp0.."
if not exist build\c24_checks mkdir build\c24_checks
call "C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat" >nul
if errorlevel 1 exit /b 1
set "C24_VENDOR_SRC=projects\03_tinyml\embedded_sw\sapphire_soc_tinyml\software\standalone\tinyml_pdti8\src"
cl /nologo /EHsc /std:c++14 /W4 /I"%C24_VENDOR_SRC%" /Iteam_work\03_ai_soc\c24 team_work\03_ai_soc\tests\test_c24_uart_format.cc "%C24_VENDOR_SRC%\tensorflow\lite\micro\micro_string.cc" /Fobuild\c24_checks\ /Febuild\c24_checks\test_c24_uart_format.exe
if errorlevel 1 exit /b 1
build\c24_checks\test_c24_uart_format.exe
exit /b %errorlevel%
