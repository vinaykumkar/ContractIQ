@echo off
rem ============================================================
rem  ContractIQ - backend launcher (portable, no hardcoded paths)
rem ============================================================
setlocal
set "PROJECT_DIR=%~dp0"
cd /d "%PROJECT_DIR%"

if not exist "%PROJECT_DIR%.venv\Scripts\python.exe" (
    echo ContractIQ is not installed on this machine.
    echo Please run setup_windows.bat first.
    pause
    exit /b 1
)
call "%PROJECT_DIR%.venv\Scripts\activate.bat"

if "%BACKEND_PORT%"=="" set "BACKEND_PORT=8000"

echo Starting ContractIQ API on http://127.0.0.1:%BACKEND_PORT% ...
echo Docs: http://127.0.0.1:%BACKEND_PORT%/docs  (press CTRL+C to stop)
cd /d "%PROJECT_DIR%backend"
python -m uvicorn app.main:app --host 127.0.0.1 --port %BACKEND_PORT%
endlocal
