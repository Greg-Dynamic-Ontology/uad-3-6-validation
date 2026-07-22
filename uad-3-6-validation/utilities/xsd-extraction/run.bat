@echo off
setlocal

REM Run the XSD Extraction Utility from this batch file's directory.
cd /d "%~dp0"

python -m xsd_extraction ^
  --input-path "..\..\specs\UAD\GSE_UAD_3.6.0_v1.3\Combined" ^
  --output-path "..\..\specs\samples\xsd_extraction"

if errorlevel 1 (
    echo.
    echo XSD extraction failed.
    exit /b 1
)

echo.
echo XSD extraction completed successfully.
exit /b 0
