@echo off
setlocal

cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo ERROR: Project virtual environment not found at .venv\Scripts\python.exe
    exit /b 1
)

if not exist "utilities\gse_constraints\rebuild_data_constraints_from_configured_workbook.py" (
    echo ERROR: Utility not found at utilities\gse_constraints\rebuild_data_constraints_from_configured_workbook.py
    exit /b 1
)

".venv\Scripts\python.exe" "utilities\gse_constraints\rebuild_data_constraints_from_configured_workbook.py" %*
exit /b %ERRORLEVEL%