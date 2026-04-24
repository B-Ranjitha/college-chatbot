@echo off
:: ─────────────────────────────────────────────────────────────────
::  BBC College AI Chatbot — Windows Run Script
::  Double-click this to start the server every time.
:: ─────────────────────────────────────────────────────────────────

echo.
echo  Starting BBC College AI Chatbot...
echo  Open http://localhost:5000 in your browser
echo  Press CTRL+C to stop
echo.

:: Activate venv and run
call venv\Scripts\activate.bat
python app.py
pause
