@echo off
rem ============================================================
rem  ContractIQ - combined launcher: backend + frontend + browser
rem ============================================================
setlocal
set "PROJECT_DIR=%~dp0"

if not exist "%PROJECT_DIR%.venv\Scripts\python.exe" (
    echo ContractIQ is not installed on this machine.
    echo Please run setup_windows.bat first.
    pause
    exit /b 1
)
if not exist "%PROJECT_DIR%frontend\node_modules" (
    echo Frontend dependencies are missing.
    echo Please run setup_windows.bat first.
    pause
    exit /b 1
)

start "ContractIQ Backend" cmd /k ""%PROJECT_DIR%run_backend.bat""
timeout /t 2 /nobreak >nul
start "ContractIQ Frontend" cmd /k ""%PROJECT_DIR%run_frontend.bat""

echo ContractIQ is starting:
echo   Backend : http://127.0.0.1:8000  (docs at /docs)
echo   Frontend: http://localhost:5173
echo Opening the browser shortly...
timeout /t 8 /nobreak >nul
start "" http://localhost:5173
echo (Close the two ContractIQ windows to stop the app.)
timeout /t 5 /nobreak >nul
endlocal
