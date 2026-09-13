@echo off
rem ============================================================
rem  ContractIQ - frontend launcher (portable, no hardcoded paths)
rem ============================================================
setlocal
set "PROJECT_DIR=%~dp0"

if not exist "%PROJECT_DIR%frontend\node_modules" (
    echo ContractIQ frontend dependencies are not installed.
    echo Please run setup_windows.bat first.
    pause
    exit /b 1
)
if not exist "%PROJECT_DIR%frontend\package.json" (
    echo ERROR: frontend\package.json is missing from this project folder.
    pause
    exit /b 1
)

echo Starting ContractIQ frontend on http://localhost:5173 ...  (press CTRL+C to stop)
cd /d "%PROJECT_DIR%frontend"
call npm run dev
endlocal
