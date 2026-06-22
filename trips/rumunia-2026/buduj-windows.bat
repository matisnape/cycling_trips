@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo Live preview. Edit tresc.md in Obsidian and save - the site refreshes itself.
echo Stop the window: Ctrl+C, then close it.
py build.py --watch || python build.py --watch
pause
