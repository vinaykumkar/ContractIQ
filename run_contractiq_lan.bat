@echo off
rem ============================================================
rem  ContractIQ - LAN launcher (production UI + API, all interfaces)
rem  Same as run_contractiq_prod.bat, but other devices on the
rem  same Wi-Fi can open the app via this PC's IP address, e.g.
rem  http://192.168.0.103:8010  (check your IP with: ipconfig)
rem  NOTE: no authentication - use on a trusted network only.
rem  Windows Firewall may ask to allow Python on first run.
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
    pause
    exit /b 1
)

call "%PROJECT_DIR%.venv\Scripts\activate.bat"

if "%BACKEND_PORT%"=="" set "BACKEND_PORT=8010"

echo Starting ContractIQ (LAN mode) on http://0.0.0.0:%BACKEND_PORT% ...
echo Local:      http://127.0.0.1:%BACKEND_PORT%
echo Your LAN:   http://<this-PC-ip>:%BACKEND_PORT%   (run: ipconfig)
echo (press CTRL+C to stop)
start "" http://127.0.0.1:%BACKEND_PORT%
cd /d "%PROJECT_DIR%backend"
python -m uvicorn app.main:app --host 0.0.0.0 --port %BACKEND_PORT%
endlocal
