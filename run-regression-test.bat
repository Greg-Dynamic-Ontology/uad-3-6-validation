@echo off
setlocal
cd /d "%~dp0"

".venv\Scripts\python.exe" -B -m pytest tests -q --tb=short --durations=10 -p no:cacheprovider
set "test_exit_code=%ERRORLEVEL%"
echo.
pause
exit /b %test_exit_code%
