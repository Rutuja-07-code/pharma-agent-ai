@echo off
setlocal

set "REPO_DIR=%~dp0"
set "APP_URL=http://127.0.0.1:8000"
set "LANGFUSE_SECRET_KEY=sk-lf-810adc95-7bd7-4bd2-9918-a0d0053c0bcf"
set "LANGFUSE_PUBLIC_KEY=pk-lf-dd69cfd9-5b66-487a-9c51-ec42b24ea620"
set "LANGFUSE_BASE_URL=https://cloud.langfuse.com"
set "LANGFUSE_HOST=https://cloud.langfuse.com"

rem Load persisted UPI settings from user environment if not already present.
if not defined UPI_ID (
  for /f "tokens=2,*" %%A in ('reg query HKCU\Environment /v UPI_ID 2^>nul ^| findstr /R /C:"UPI_ID"') do set "UPI_ID=%%B"
)
if not defined UPI_PAYEE_NAME (
  for /f "tokens=2,*" %%A in ('reg query HKCU\Environment /v UPI_PAYEE_NAME 2^>nul ^| findstr /R /C:"UPI_PAYEE_NAME"') do set "UPI_PAYEE_NAME=%%B"
)
if not defined UPI_ID (
  echo WARNING: UPI_ID is not set. Configure it with: setx UPI_ID yourname@oksbi
)

netstat -ano | findstr ":8000" >nul
if %errorlevel%==0 (
  echo Pharma app is already running on port 8000.
) else (
  start "Pharma Backend" cmd /k "set UPI_ID=%UPI_ID% && set UPI_PAYEE_NAME=%UPI_PAYEE_NAME% && cd /d "%REPO_DIR%backend\app" && if exist "%REPO_DIR%.venv\Scripts\activate.bat" call "%REPO_DIR%.venv\Scripts\activate.bat" && uvicorn main:app --reload --host 127.0.0.1 --port 8000"
  timeout /t 2 >nul
  echo Started backend.
)

start "" "%APP_URL%"
echo Opened %APP_URL%

endlocal
