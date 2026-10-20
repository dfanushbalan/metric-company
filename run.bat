@echo off
title Appointment Slot Booker
color 0b
cls
echo ======================================================================
echo          APPOINTMENT SLOT BOOKER - ONE-CLICK LAUNCHER
echo ======================================================================
echo.

cd /d "%~dp0backend"

echo [Step 1/3] Checking Python installation...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Python is not installed or not in your system PATH!
    echo Please download and install Python from: https://www.python.org/downloads/
    echo (Make sure to check "Add Python to PATH" during installation)
    echo.
    pause
    exit /b
)
python --version

echo.
echo [Step 2/3] Installing and verifying backend dependencies...
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo.
    echo [WARNING] Encountered an issue while installing packages.
    echo Trying to proceed anyway...
)

echo.
echo [Step 3/3] Launching Flask Application on http://127.0.0.1:5000 ...
echo Opening your web browser in 2 seconds...
timeout /t 2 /nobreak >nul
start http://127.0.0.1:5000

echo.
echo ======================================================================
echo   Server is running! Leave this window open while using the app.
echo   Press Ctrl+C in this window anytime to stop the server.
echo ======================================================================
echo.
python app.py

pause
