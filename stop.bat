@echo off
rem Stops whatever is currently listening on StoreOps' port (default 8010),
rem regardless of how it was started or whether its window is still open.
rem Usage: stop.bat [port]

setlocal
set "PORT=%~1"
if "%PORT%"=="" set "PORT=8010"

set "TARGET_PID="
for /f "usebackq delims=" %%P in (`powershell -NoProfile -Command ^
    "(Get-NetTCPConnection -LocalPort %PORT% -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1 -ExpandProperty OwningProcess)"`) do (
    set "TARGET_PID=%%P"
)

if not defined TARGET_PID (
    echo Nothing is listening on port %PORT%. Nothing to stop.
    endlocal
    exit /b 0
)

echo Stopping process %TARGET_PID% listening on port %PORT% ...
taskkill /F /PID %TARGET_PID%
if errorlevel 1 (
    echo Could not stop process %TARGET_PID%. It may require elevation, or may
    echo have already exited.
    endlocal
    exit /b 1
)

echo Done.
endlocal
