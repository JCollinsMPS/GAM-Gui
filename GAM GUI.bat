@echo off
where py >nul 2>&1 && py "%~dp0main.py" && goto :eof
where python >nul 2>&1 && python "%~dp0main.py" && goto :eof
echo Python was not found. Please install Python from https://www.python.org/downloads/
pause
