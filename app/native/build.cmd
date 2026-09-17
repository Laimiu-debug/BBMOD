@echo off
setlocal
cd /d "%~dp0.."
set "BBMOD_NATIVE_OUT=build\native"
set "BBMOD_CAPTURE_FLAG="
if "%~1"=="--capture" set "BBMOD_NATIVE_OUT=build\native-test"
if "%~1"=="--capture" set "BBMOD_CAPTURE_FLAG=/DBBMOD_CAPTURE"
if not exist "%BBMOD_NATIVE_OUT%" mkdir "%BBMOD_NATIVE_OUT%"
if not exist "%BBMOD_NATIVE_OUT%\obj" mkdir "%BBMOD_NATIVE_OUT%\obj"
call "%ProgramFiles(x86)%\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvarsall.bat" x86 >nul
if errorlevel 1 exit /b 1
cl /nologo /O2 /MT /EHsc /std:c++17 /utf-8 /DUNICODE /D_UNICODE %BBMOD_CAPTURE_FLAG% /LD /Fo"%BBMOD_NATIVE_OUT%\obj\\" native\han_font.cpp native\vendor\minhook\src\buffer.c native\vendor\minhook\src\hook.c native\vendor\minhook\src\trampoline.c native\vendor\minhook\src\hde\hde32.c /link user32.lib gdi32.lib opengl32.lib bcrypt.lib /OUT:%BBMOD_NATIVE_OUT%\bbmod_han.dll
if errorlevel 1 exit /b 1
cl /nologo /O2 /MT /EHsc /std:c++17 /utf-8 /DUNICODE /D_UNICODE /Fo"%BBMOD_NATIVE_OUT%\obj\\" native\launch_game.cpp /link /OUT:%BBMOD_NATIVE_OUT%\bbmod_launch.exe
exit /b %errorlevel%
