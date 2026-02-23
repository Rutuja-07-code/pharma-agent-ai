@echo off
setlocal

set "REPO_DIR=%~dp0"
set "APP_URL=http://127.0.0.1:8000"

netstat -ano | findstr ":8000" >nul
if %errorlevel%==0 (
  echo Pharma app is already running on port 8000.
) else (
  start "Pharma Backend" cmd /k "cd /d "%REPO_DIR%backend\app" && if exist "%REPO_DIR%.venv\Scripts\activate.bat" call "%REPO_DIR%.venv\Scripts\activate.bat" && uvicorn main:app --reload --host 127.0.0.1 --port 8000"
  timeout /t 2 >nul
  echo Started backend.
)

start "" "%APP_URL%"
echo Opened %APP_URL%

endlocal
