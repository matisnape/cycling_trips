@echo off
chcp 65001 >nul
cd /d "%~dp0"
rem Live preview of a trip. Usage: build-windows.bat <slug>
rem Without an argument (e.g. after a double-click) it asks which trip to open.
set "SLUG=%~1"
if not "%SLUG%"=="" goto have
echo Available trips:
for /f "delims=" %%d in ('dir /b /ad trips ^| findstr /v /b "_"') do echo   %%d
set /p SLUG=Trip name: 
:have
if "%SLUG%"=="" (
  echo No trip given.
  pause
  exit /b 1
)
echo Live preview: %SLUG%. Edit trips\%SLUG%\tresc.md and save - the site refreshes itself.
echo Stop: Ctrl+C, then close this window.
where py >nul 2>nul
if %errorlevel%==0 (
  py build.py %SLUG% --watch
) else (
  python build.py %SLUG% --watch
)
pause
