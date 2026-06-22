@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo Podglad na zywo. Edytuj tresc.md w Obsidianie, zapisuj - strona odswiezy sie sama.
echo Zatrzymaj okno: Ctrl+C, potem zamknij.
py build.py --watch || python build.py --watch
pause
