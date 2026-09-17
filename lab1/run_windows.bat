@echo off
chcp 65001 > nul
cd /d "%~dp0"

echo [1/3] Проверка виртуального окружения...
if not exist .venv (
    echo Создание виртуального окружения .venv...
    python -m venv .venv
)

echo [2/3] Активация окружения и установка PyQt6...
call .venv\Scripts\activate
pip install -r requirements.txt --quiet

echo [3/3] Запуск лабораторной работы...
python main.py

echo.
echo Программа завершила работу.
pause

