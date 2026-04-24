@echo off
:: ─────────────────────────────────────────────────────────────────
::  BBC College AI Chatbot — Windows Setup Script
::  Run this ONCE to set up your environment.
::  Double-click or run from PowerShell:  .\setup_windows.bat
:: ─────────────────────────────────────────────────────────────────

echo.
echo ========================================
echo  BBC College AI — Windows Setup
echo ========================================
echo.

:: Step 1 — Create virtual environment
echo [1/5] Creating virtual environment...
python -m venv venv
if errorlevel 1 (
    echo ERROR: Python not found. Install Python 3.10+ from https://python.org
    pause
    exit /b 1
)
echo       Done.

:: Step 2 — Activate virtual environment
echo [2/5] Activating virtual environment...
call venv\Scripts\activate.bat

:: Step 3 — Upgrade pip silently
echo [3/5] Upgrading pip...
python -m pip install --upgrade pip --quiet

:: Step 4 — Install all dependencies
echo [4/5] Installing dependencies (this may take 2-5 minutes)...
pip install -r requirements.txt
if errorlevel 1 (
    echo ERROR: Dependency installation failed. Check the error above.
    pause
    exit /b 1
)
echo       Done.

:: Step 5 — Copy .env if it does not exist
echo [5/5] Setting up .env file...
if not exist .env (
    copy .env.example .env
    echo       .env created from template.
    echo.
    echo  *** IMPORTANT: Open .env and set your OPENAI_API_KEY ***
    echo  *** The chatbot works without it but uses FAQ-only mode ***
) else (
    echo       .env already exists — skipping.
)

echo.
echo ========================================
echo  Setup complete!
echo ========================================
echo.
echo  To START the server:
echo    1. venv\Scripts\activate
echo    2. python app.py
echo    3. Open http://localhost:5000 in your browser
echo.
echo  Admin login:
echo    Email:    admin@bbc.edu.in
echo    Password: admin@123
echo.
pause
