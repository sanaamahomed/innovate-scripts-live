@echo off
REM Innovate Assure - one-time setup on Windows. Run by double-clicking.
cd /d "%~dp0.."
where python >nul 2>nul || (echo Python is not installed. Install Python 3.11 or newer from python.org ^(tick "Add to PATH"^) and run this again. & pause & exit /b 1)
where ffmpeg >nul 2>nul || (echo ffmpeg is missing. Open a terminal and run:  winget install Gyan.FFmpeg   then run this again. & pause & exit /b 1)
if not exist .venv ( python -m venv .venv || (echo Could not create the Python environment. & pause & exit /b 1) )
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements.txt || (echo Install failed. Check your internet connection. & pause & exit /b 1)
if not exist .env ( copy .env.example .env >nul & echo Created .env - opening it so you can set APP_PASSWORD. & notepad .env )
echo.
echo Setup finished. Double-click windows\start.bat to run Assure.
echo The first call you upload downloads the speech model ^(about 1.6 GB, one time^).
pause
