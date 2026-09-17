@echo off
setlocal EnableExtensions

rem ============================================================
rem ContractIQ - Local Application Launcher
rem Starts Backend + Frontend and opens the browser
rem ============================================================

set "ROOT=%~dp0"

echo.
echo ============================================================
echo                  ContractIQ Launcher
echo ============================================================
echo.

rem Check Python virtual environment
if not exist "%ROOT%.venv\Scripts\python.exe" (
    echo [ERROR] Python virtual environment not found.
    echo Please run setup_windows.bat first.
    echo.
    pause
    exit /b 1
)

rem Check frontend dependencies
if not exist "%ROOT%frontend\node_modules" (
    echo [ERROR] Frontend dependencies not found.
    echo Please run setup_windows.bat first.
    echo.
    pause
    exit /b 1
)

echo [1/3] Starting ContractIQ Backend...
start "ContractIQ Backend" cmd /k "%ROOT%run_backend.bat"

timeout /t 2 /nobreak >nul

echo [2/3] Starting ContractIQ Frontend...
start "ContractIQ Frontend" cmd /k "%ROOT%run_frontend.bat"

echo.
echo Backend  : http://127.0.0.1:8000
echo API Docs : http://127.0.0.1:8000/docs
echo Frontend : http://localhost:5173
echo.

echo [3/3] Waiting for services to start...
timeout /t 8 /nobreak >nul

echo Opening ContractIQ in your browser...
start "" "http://localhost:5173"

echo.
echo ============================================================
echo ContractIQ has been launched successfully.
echo Close the Backend and Frontend windows to stop the app.
echo ============================================================
echo.

timeout /t 5 /nobreak >nul
endlocal
