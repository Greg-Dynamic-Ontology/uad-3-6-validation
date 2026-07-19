@echo off
REM ============================================================================
REM test-xsd-extraction.bat
REM Runs the XSD Extraction utility against the sample UAD schemas.
REM ============================================================================

setlocal
cd /d "%~dp0"

echo.
echo ============================================================
echo Running XSD Extraction Utility
echo ============================================================
echo.

python -m xsd_extraction ^
  --input-path "..\..\specs\UAD\GSE_UAD_3.6.0_v1.3\Combined" ^
  --output-path "..\..\specs\samples\xsd_extraction"

if errorlevel 1 (
    echo.
    echo *** TEST FAILED ***
    exit /b 1
)

echo.
echo *** TEST PASSED ***
exit /b 0
