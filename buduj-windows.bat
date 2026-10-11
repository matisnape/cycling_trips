@echo off
chcp 65001 >nul
cd /d "%~dp0"
rem Podglad na zywo wyprawy. Uzycie: buduj-windows.bat <slug>
rem Bez argumentu (np. po dwukliku) pyta o wyprawe.
set "SLUG=%~1"
if not "%SLUG%"=="" goto have
echo Dostepne wyprawy:
for /f "delims=" %%d in ('dir /b /ad trips ^| findstr /v /b "_"') do echo   %%d
set /p SLUG=Podaj nazwe wyprawy: 
:have
if "%SLUG%"=="" (
  echo Nie podano wyprawy.
  pause
  exit /b 1
)
echo Podglad na zywo: %SLUG%. Edytuj trips\%SLUG%\tresc.md i zapisz - strona odswiezy sie sama.
echo Zatrzymanie: Ctrl+C, potem zamknij okno.
where py >nul 2>nul
if %errorlevel%==0 (
  py build.py %SLUG% --watch
) else (
  python build.py %SLUG% --watch
)
pause
