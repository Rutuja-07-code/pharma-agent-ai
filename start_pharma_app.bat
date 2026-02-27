@echo off
setlocal

set "REPO_DIR=%~dp0"
set "APP_URL=http://127.0.0.1:8000"
set "LANGFUSE_SECRET_KEY=sk-lf-810adc95-7bd7-4bd2-9918-a0d0053c0bcf"
set "LANGFUSE_PUBLIC_KEY=pk-lf-dd69cfd9-5b66-487a-9c51-ec42b24ea620"
set "LANGFUSE_BASE_URL=https://cloud.langfuse.com"
set "LANGFUSE_HOST=https://cloud.langfuse.com"

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
