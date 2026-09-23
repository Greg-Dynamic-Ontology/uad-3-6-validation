@echo off
setlocal
cd /d "%~dp0"

".venv\Scripts\python.exe" -B -m pytest tests data\uad36-test-suite\tests\test_required_data_acceptance.py data\uad36-test-suite\tests\test_required_data_rdf.py -q --tb=short -p no:cacheprovider

set "test_exit_code=%ERRORLEVEL%"
echo.
pause
exit /b %test_exit_code%