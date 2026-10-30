@echo off
cd /d "%~dp0"
".venv\Scripts\python.exe" "restart_visitready.py"
if errorlevel 1 pause
