@echo off
rem ============================================================
rem  ContractIQ - PRODUCTION launcher (single port, built UI)
rem  Serves the built frontend + API together from one server.
rem  Run setup_windows.bat once before using this.
rem ============================================================
setlocal
set "PROJECT_DIR=%~dp0"

if not exist "%PROJECT_DIR%.venv\Scripts\python.exe" (
    echo ContractIQ is not installed on this machine.
    echo Please run setup_windows.bat first.
    pause
    exit /b 1
)
if not exist "%PROJECT_DIR%frontend\dist\index.html" (
    echo Production frontend build not found.
    echo Run:  cd frontend ^&^& npm run build
    echo (or use run_contractiq.bat for the dev-server mode^)
    pause
    exit /b 1
)

call "%PROJECT_DIR%.venv\Scripts\activate.bat"

if "%BACKEND_PORT%"=="" set "BACKEND_PORT=8010"

echo Starting ContractIQ (production) on http://127.0.0.1:%BACKEND_PORT% ...
echo API docs: http://127.0.0.1:%BACKEND_PORT%/docs  (press CTRL+C to stop)
start "" http://127.0.0.1:%BACKEND_PORT%cd /d "%PROJECT_DIR%backend"
python -m uvicorn app.main:app --host 127.0.0.1 --port %BACKEND_PORT%
endlocal
