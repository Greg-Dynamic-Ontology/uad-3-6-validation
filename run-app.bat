@echo off
setlocal

REM Change to the directory containing this batch file
cd /d "%~dp0"

echo ====================================================
echo UAD 3.6 Validation
echo ====================================================
echo.

REM Activate the virtual environment if present
if exist ".venv\Scripts\activate.bat" (
    call ".venv\Scripts\activate.bat"
) else (
    echo WARNING: .venv not found. Using system Python.
    echo.
)

echo Starting FastAPI application...
echo.
echo Open your browser to:
echo     http://127.0.0.1:8000/
echo or
echo     http://127.0.0.1:8000/validation/
echo.
echo Press Ctrl+C to stop the server.
echo.

python -m uvicorn app.main:app --reload

echo.
echo Server stopped.
pause