@echo off
rem ============================================================
rem  ContractIQ - one-click setup for a fresh Windows laptop.
rem  Creates a project-local .venv, installs Python + Node
rem  dependencies, prepares storage, verifies the bundled model.
rem  Works from ANY folder (path resolved from this script).
rem ============================================================
setlocal enabledelayedexpansion
set "PROJECT_DIR=%~dp0"
cd /d "%PROJECT_DIR%"

echo ==============================================
echo  ContractIQ Setup
echo  Project folder: %PROJECT_DIR%
echo ==============================================

rem ---------- 1. Python ----------
set "PY=python"
%PY% --version >nul 2>&1
if errorlevel 1 (
    echo [FAIL] Python was not found on PATH.
    echo        Install Python 3.11 or newer from https://www.python.org/downloads/
    echo        and tick "Add python.exe to PATH" during installation.
    goto :fail
)
for /f "tokens=2" %%v in ('%PY% --version 2^>^&1') do set "PYVER=%%v"
echo [OK] Python %PYVER% detected.
rem tested with 3.11; supported range 3.11 - 3.13
for /f "tokens=1,2 delims=." %%a in ("%PYVER%") do set "PYMAJ=%%a" && set "PYMIN=%%b"
if %PYMAJ% LSS 3 goto :badpython
if %PYMAJ% EQU 3 if %PYMIN% LSS 11 goto :badpython
if %PYMAJ% EQU 3 if %PYMIN% GEQ 14 goto :badpython

rem ---------- 2. virtual environment ----------
if not exist "%PROJECT_DIR%.venv\Scripts\python.exe" (
    echo [..] Creating virtual environment .venv ...
    %PY% -m venv .venv
    if errorlevel 1 ( echo [FAIL] Could not create .venv & goto :fail )
) else (
    echo [OK] .venv already exists - reusing it.
)
call "%PROJECT_DIR%.venv\Scripts\activate.bat"
%PY% -m pip install --upgrade pip >nul 2>&1

rem ---------- 3. PyTorch strategy: CPU baseline, optional official CUDA build ----------
set "TORCH_INDEX="
nvidia-smi >nul 2>&1
if errorlevel 1 (
    echo [INFO] No NVIDIA GPU detected - installing CPU PyTorch build.
) else (
    echo [INFO] NVIDIA GPU detected.
    set /p "USE_GPU=Install the CUDA-enabled PyTorch build for it? [Y/n]: "
    if /i not "!USE_GPU!"=="n" set "TORCH_INDEX=--index-url https://download.pytorch.org/whl/cu130"
)
if defined TORCH_INDEX (
    echo [..] Installing CUDA-enabled PyTorch from the official PyTorch index ...
    %PY% -m pip install "torch==2.13.0+cu130" --index-url https://download.pytorch.org/whl/cu130
    if errorlevel 1 (
        echo [WARN] CUDA PyTorch install failed - falling back to the CPU build.
        %PY% -m pip install "torch==2.13.0"
    )
) else (
    echo [..] Installing CPU PyTorch ...
    %PY% -m pip install "torch==2.13.0"
    if errorlevel 1 ( echo [FAIL] PyTorch installation failed. & goto :fail )
)

rem ---------- 4. Python requirements ----------
echo [..] Installing Python requirements (backend + ML) ...
%PY% -m pip install -r "%PROJECT_DIR%backend\requirements.txt" -r "%PROJECT_DIR%ml\requirements.txt" --no-deps 2>nul
%PY% -m pip install -r "%PROJECT_DIR%backend\requirements.txt" -r "%PROJECT_DIR%ml\requirements.txt"
if errorlevel 1 ( echo [FAIL] Python requirements failed to install. & goto :fail )

rem ---------- 5. Node ----------
set "NODE_OK=1"
node --version >nul 2>&1
if errorlevel 1 (
    echo [WARN] Node.js was not found on PATH.
    echo        The frontend needs Node.js 20+ from https://nodejs.org/
    echo        Install it and re-run this setup to install frontend dependencies.
    set "NODE_OK="
) else (
    for /f "tokens=1" %%v in ('node --version') do echo [OK] Node %%v detected.
)

if defined NODE_OK (
    if not exist "%PROJECT_DIR%frontend\package.json" (
        echo [FAIL] frontend\package.json is missing.
        goto :fail
    )
    echo [..] Installing frontend dependencies via npm ci ...
    cd /d "%PROJECT_DIR%frontend"
    if exist package-lock.json (
        call npm ci
    ) else (
        call npm install
    )
    if errorlevel 1 ( echo [FAIL] npm install failed. & goto :fail )
    cd /d "%PROJECT_DIR%"
)

rem ---------- 6. storage + env + database + model ----------
if not exist "%PROJECT_DIR%storage\uploads" mkdir "%PROJECT_DIR%storage\uploads"
if not exist "%PROJECT_DIR%storage\temp" mkdir "%PROJECT_DIR%storage\temp"
echo [OK] Storage directories ready (storage\uploads, storage\temp).

if not exist "%PROJECT_DIR%.env" (
    copy "%PROJECT_DIR%.env.example" "%PROJECT_DIR%.env" >nul
    echo [OK] Created .env from .env.example - edit it to customise, optional.
) else (
    echo [OK] Existing .env left untouched.
)

echo [..] Verifying bundled model, database and imports ...
%PY% "%PROJECT_DIR%scripts\verify_install.py"
if errorlevel 1 ( echo [FAIL] Installation verification failed. & goto :fail )

echo.
echo ==============================================
echo  ContractIQ setup finished successfully!
echo  Next: double-click run_contractiq.bat
echo ==============================================
endlocal
exit /b 0

:badpython
echo [FAIL] Python %PYVER% is not supported. This project is tested with Python 3.11 (supported: 3.11 - 3.13).
goto :fail

:fail
echo.
echo [FAIL] Setup did not complete. Fix the message above and re-run setup_windows.bat.
endlocal
exit /b 1
