@echo off
setlocal
REM Change to repo root (this script lives in tools\)
cd /d "%~dp0.."

REM Create venv if missing
if not exist .venv\Scripts\python.exe (
  echo Creating virtual environment...
  py -3.11 -m venv .venv || goto :err
)

REM Activate venv
call .\.venv\Scripts\activate
if errorlevel 1 goto err

REM Install/upgrade deps
python -m pip install --upgrade pip
if errorlevel 1 goto err
pip install -r requirements.txt
if errorlevel 1 goto err

REM Run app
python app.py
exit /b %errorlevel%

:err
echo.
echo Failed to set up or run the app. Ensure Python 3.9+ is installed and available via the 'py' launcher.
exit /b 1
