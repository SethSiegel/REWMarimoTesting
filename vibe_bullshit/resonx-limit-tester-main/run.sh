#!/bin/bash

if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv .venv
fi

# Find the correct Python executable in the venv
if [ -f ".venv/bin/python3" ]; then
    PYTHON=".venv/bin/python3"
elif [ -f ".venv/bin/python" ]; then
    PYTHON=".venv/bin/python"
else
    echo "Error: Python not found in virtual environment"
    exit 1
fi

echo "Installing dependencies..."
.venv/bin/pip install -q -r requirements.txt

echo ""
echo "========================================"
echo "  ResonX Limit Tester Server"
echo "========================================"
echo ""
echo "Starting server on http://localhost:5000"
echo ""
echo "Open your browser and navigate to:"
echo "  http://localhost:5000"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

$PYTHON server.py