@echo off
REM Starts Innovate Assure for the whole team on port 8501: http://<this-pc-name>:8501
cd /d "%~dp0.."
if not exist .venv\Scripts\activate.bat ( echo Run windows\install.bat first. & pause & exit /b 1 )
call .venv\Scripts\activate.bat
if "%QA_PORT%"=="" set QA_PORT=8501
echo Assure is starting at http://%COMPUTERNAME%:%QA_PORT%  ^(leave this window open^)
python -m uvicorn server:app --host 0.0.0.0 --port %QA_PORT%
pause
