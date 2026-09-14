@echo off
cd /d "%~dp0"
call .venv\Scripts\activate
python gui_hub.py
pause
