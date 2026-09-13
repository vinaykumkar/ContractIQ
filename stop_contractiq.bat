@echo off
rem ============================================================
rem  ContractIQ - stop the app started by run_contractiq.bat.
rem  Filters by window title so OTHER Python/Node processes on
rem  the machine are never touched.
rem ============================================================
echo Stopping ContractIQ windows (Backend / Frontend)...
taskkill /FI "WINDOWTITLE eq ContractIQ Backend*" /T /F >nul 2>&1
taskkill /FI "WINDOWTITLE eq ContractIQ Frontend*" /T /F >nul 2>&1
echo Done. If a window remains open, close it manually.
pause
