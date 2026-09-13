@echo off
rem StoreOps local startup (Windows).
rem Creates/updates the venv, installs deps, starts the API on port 8010,
rem waits for /health, then opens the Swagger UI (all endpoints) in your
rem default browser. Ctrl+C (or closing this window) stops the server.
rem
rem Self-healing: if a previous run wasn't shut down cleanly (window closed
rem without Ctrl+C, terminal killed, etc.) and left a process still bound
rem to the port, this script detects and stops it before starting a new
rem one -- that is exactly what avoids "WinError 10048: only one usage of
rem each socket address is normally permitted" on the next run. You can
rem also run stop.bat at any time to explicitly stop whatever is currently
rem listening on the port.

setlocal EnableDelayedExpansion

set "ROOT=%~dp0"
cd /d "%ROOT%"

set "HOST=127.0.0.1"
set "PORT=8010"
set "VENV_DIR=.venv"

echo === StoreOps startup ===
echo Project root: %ROOT%

rem --- locate a Python interpreter ---
set "PY_CMD="
where python >nul 2>nul
if not errorlevel 1 (
    set "PY_CMD=python"
) else (
    where py >nul 2>nul
    if not errorlevel 1 (
        set "PY_CMD=py -3"
    )
)
if "%PY_CMD%"=="" (
    echo ERROR: No Python interpreter found on PATH. Install Python 3.11+ and re-run.
    exit /b 1
)

rem --- create the venv if it doesn't exist yet ---
if not exist "%VENV_DIR%\Scripts\python.exe" (
    echo Creating virtual environment in "%VENV_DIR%" ...
    %PY_CMD% -m venv "%VENV_DIR%"
    if errorlevel 1 (
        echo ERROR: Failed to create the virtual environment.
        exit /b 1
    )
) else (
    echo Using existing virtual environment in "%VENV_DIR%".
)

call "%VENV_DIR%\Scripts\activate.bat"
if errorlevel 1 (
    echo ERROR: Failed to activate the virtual environment.
    exit /b 1
)

echo Installing/updating dependencies ...
python -m pip install --upgrade pip --quiet
if errorlevel 1 (
    echo ERROR: Failed to upgrade pip.
    exit /b 1
)
pip install -r requirements.txt --quiet
if errorlevel 1 (
    echo ERROR: Failed to install dependencies from requirements.txt.
    exit /b 1
)
pip install -e . --quiet
if errorlevel 1 (
    echo ERROR: Failed to install the StoreOps app package.
    exit /b 1
)
echo Dependencies ready.

rem --- self-heal: stop whatever is already bound to HOST:PORT, if anything
rem     (a stale process from a previous run that wasn't shut down cleanly) ---
set "STALE_PID="
for /f "usebackq delims=" %%P in (`powershell -NoProfile -Command ^
    "(Get-NetTCPConnection -LocalPort %PORT% -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1 -ExpandProperty OwningProcess)"`) do (
    set "STALE_PID=%%P"
)
if defined STALE_PID (
    echo Port %PORT% is already in use by process %STALE_PID% -- likely a
    echo leftover from a previous run that wasn't shut down cleanly. Stopping it ...
    taskkill /F /PID %STALE_PID% >nul 2>nul
    rem 1-second delay -- see wait_and_open.bat for why this is ping, not timeout.
    ping -n 2 127.0.0.1 >nul
)

rem --- background helper: waits for /health, then opens the API docs ---
start "StoreOps opener" /min "%ROOT%scripts\wait_and_open.bat" %HOST% %PORT%

echo.
echo Starting StoreOps on http://%HOST%:%PORT%
echo All APIs are documented at http://%HOST%:%PORT%/docs -- it opens
echo automatically once /health reports ready.
echo Press Ctrl+C to stop the server (or run stop.bat from another window).
echo.

uvicorn app.main:app --host %HOST% --port %PORT%

echo.
echo StoreOps has stopped.
endlocal
