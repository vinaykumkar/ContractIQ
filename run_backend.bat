@echo off
setlocal

REM ============================================================
REM ContractIQ - Backend Launcher
REM Portable launcher using the project directory
REM ============================================================

REM Move to the folder where this BAT file is located
cd /d "%~dp0"

REM Check virtual environment
if not exist ".venv\Scripts\python.exe" (
    echo.
    echo [ERROR] ContractIQ virtual environment not found.
    echo.
    echo Please run setup_windows.bat first.
    echo.
    pause
    exit /b 1
)

REM Set default backend port if not already provided
if not defined BACKEND_PORT set "BACKEND_PORT=8000"

echo.
echo ============================================================
echo                 ContractIQ Backend
echo ============================================================
echo.
echo Project : %CD%
echo Port    : %BACKEND_PORT%
echo API     : http://127.0.0.1:%BACKEND_PORT%
echo Docs    : http://127.0.0.1:%BACKEND_PORT%/docs
echo.
echo Starting backend...
echo Press CTRL+C to stop the server.
echo.

REM Start backend using the project's Python environment
".venv\Scripts\python.exe" -m uvicorn backend.app.main:app --host 127.0.0.1 --port %BACKEND_PORT%

echo.
echo ContractIQ backend has stopped.
pause

endlocal
