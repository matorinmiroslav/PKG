@echo off
cd /d "%~dp0"

echo [1/3] Checking virtual environment...
if not exist .venv (
    echo Creating .venv...
    python -m venv .venv
)

echo [2/3] Activating environment and installing PyQt6...
call .venv\Scripts\activate
pip install -r requirements.txt --quiet

echo [3/3] Running Python script...
python main.py

echo.
echo Process finished.
pause
