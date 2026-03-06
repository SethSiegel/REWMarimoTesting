@echo off
setlocal

set "SCRIPT_DIR=%~dp0"
for %%I in ("%SCRIPT_DIR%..") do set "REPO_DIR=%%~fI"
cd /d "%REPO_DIR%"

where uv >NUL 2>&1
if errorlevel 1 (
    echo [ERROR] 'uv' was not found in PATH.
    echo Install uv first, then run this launcher again.
    pause
    exit /b 1
)

echo Launching marimo dashboard for notebooks...
uv run marimo run notebooks --sandbox
set "EXIT_CODE=%ERRORLEVEL%"

if not "%EXIT_CODE%"=="0" (
    echo.
    echo marimo exited with code %EXIT_CODE%.
    pause
)

exit /b %EXIT_CODE%
