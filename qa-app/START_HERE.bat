@echo off
setlocal EnableDelayedExpansion
title Innovate Assure - setup and start
cd /d "%~dp0"
echo.
echo ===== Innovate Assure: setup and start =====
echo.

REM --- 1. Python and ffmpeg (installed automatically if missing) ---
set NEEDRESTART=0
python --version >nul 2>nul
if errorlevel 1 (
  where winget >nul 2>nul || (echo This PC has no "winget". Install "App Installer" from the Microsoft Store, then double-click this file again. & pause & exit /b 1)
  echo Installing Python ^(one time^)...
  winget install -e --id Python.Python.3.12 --accept-package-agreements --accept-source-agreements
  set NEEDRESTART=1
)
where ffmpeg >nul 2>nul
if errorlevel 1 (
  where winget >nul 2>nul || (echo This PC has no "winget". Install "App Installer" from the Microsoft Store, then double-click this file again. & pause & exit /b 1)
  echo Installing ffmpeg ^(one time^)...
  winget install -e --id Gyan.FFmpeg --accept-package-agreements --accept-source-agreements
  set NEEDRESTART=1
)
if "!NEEDRESTART!"=="1" (
  echo.
  echo Something was just installed. Please CLOSE this window and double-click START_HERE.bat once more.
  pause
  exit /b 0
)

REM --- 2. The app itself ---
if not exist .venv (
  echo Setting up Assure ^(one time, a few minutes^)...
  python -m venv .venv || (echo Could not create the Python environment. & pause & exit /b 1)
)
call .venv\Scripts\activate.bat
python -m pip install --quiet --upgrade pip
pip install --quiet -r requirements.txt || (echo Install failed. Check the internet connection and try again. & pause & exit /b 1)

REM --- 3. Two questions (first run only) ---
if not exist .env (
  echo.
  echo Two quick questions. Use letters and numbers only for the password.
  set /p PW=1. Choose a password for the team to open Assure: 
  echo.
  echo 2. Paste your Claude API key ^(starts with sk-ant-^) and press Enter.
  echo    If you do not have one, just press Enter ^(calls will still be transcribed, but marking needs a key^).
  set /p KEY=Key: 
  > .env echo APP_PASSWORD=!PW!
  >> .env echo ENABLED_PRODUCTS=ns
  >> .env echo TRANSCRIBER=whisper
  if "!KEY!"=="" ( >> .env echo ANALYSIS_MODE=cowork ) else ( >> .env echo ANALYSIS_MODE=api & >> .env echo ANTHROPIC_API_KEY=!KEY! )
)

REM --- 4. Start, and open the page ---
if "%QA_PORT%"=="" set QA_PORT=8501
echo.
echo Assure is starting. Your browser will open at http://localhost:%QA_PORT%
echo Team members on the same network can use http://%COMPUTERNAME%:%QA_PORT%
echo Log in with any username and the password you chose. KEEP THIS WINDOW OPEN.
echo The first call you upload downloads the speech model ^(about 1.6 GB, one time^).
echo If Windows asks about the firewall, click Allow.
echo.
start "" cmd /c "timeout /t 8 /nobreak >nul & start http://localhost:%QA_PORT%"
python -m uvicorn server:app --host 0.0.0.0 --port %QA_PORT%
pause
