@echo off

if not exist ".venv" (
    echo Creating virtual environment...
    python -m venv .venv
)

echo Activating virtual environment...
call .venv\Scripts\activate.bat

echo Installing dependencies...
pip install -q -r requirements.txt

echo.
echo ========================================
echo   ResonX Limit Tester Server
echo ========================================
echo.
echo Starting server on http://localhost:5000
echo.
echo Open your browser and navigate to:
echo   http://localhost:5000
echo.
echo Press Ctrl+C to stop the server
echo.

python server.py
