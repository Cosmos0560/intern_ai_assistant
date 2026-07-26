@echo off
REM ============================================================
REM   Lumen - one-click start for Windows.
REM   Double-click this file. It sets everything up the first
REM   time, then opens the app in your browser.
REM ============================================================
cd /d "%~dp0"

echo --------------------------------------------------
echo   Starting Lumen...
echo --------------------------------------------------

REM 1) Make sure Python exists.
where python >nul 2>&1
if errorlevel 1 (
  echo   [X] Python is not installed.
  echo       Install it from https://www.python.org/downloads/
  echo       IMPORTANT: tick "Add Python to PATH" during install.
  pause
  exit /b 1
)

REM 2) Create the virtual environment the first time.
if not exist ".venv\Scripts\python.exe" (
  echo   - First run: creating environment (takes a minute)...
  python -m venv .venv || (echo   [X] Could not create environment. & pause & exit /b 1)
)

REM 3) Install / update libraries (quiet, safe to repeat).
echo   - Checking libraries...
".venv\Scripts\python.exe" -m pip install --quiet --upgrade pip
".venv\Scripts\python.exe" -m pip install --quiet -r requirements.txt || (echo   [X] Install failed. & pause & exit /b 1)

REM 4) Open the browser after a short delay.
start "" cmd /c "timeout /t 3 >nul & start http://127.0.0.1:5000"

echo --------------------------------------------------
echo   Lumen is ready -^>  http://127.0.0.1:5000
echo   (Keep this window open. Close it to stop the app.)
echo --------------------------------------------------

REM 5) Run the server.
".venv\Scripts\python.exe" app.py
pause
