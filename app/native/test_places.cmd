@echo off
setlocal
cd /d "%~dp0.."
if not exist "build\session-place-names" mkdir "build\session-place-names"
call "%ProgramFiles(x86)%\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvarsall.bat" x86 >nul
if errorlevel 1 exit /b 1
cl /nologo /O2 /MT /EHsc /std:c++17 /utf-8 /Fo"build\session-place-names\native-test.obj" tests\native_place_display.cpp /link build\native\obj\buffer.obj build\native\obj\hook.obj build\native\obj\trampoline.obj build\native\obj\hde32.obj user32.lib gdi32.lib opengl32.lib bcrypt.lib /OUT:build\session-place-names\native-test.exe
if errorlevel 1 exit /b 1
build\session-place-names\native-test.exe "%~1" "build\full-l10n\font-research\mapped-image.bin"
exit /b %errorlevel%
