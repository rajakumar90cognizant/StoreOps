@echo off
rem Helper for start.bat: polls GET /health until it returns 200, then opens
rem the Swagger UI (all APIs) in the default browser. Exits either way --
rem it does not manage the server's lifecycle.

setlocal
set "HOST=%~1"
set "PORT=%~2"
if "%HOST%"=="" set "HOST=127.0.0.1"
if "%PORT%"=="" set "PORT=8010"
set "URL=http://%HOST%:%PORT%"
set "MAX_TRIES=60"
set "TRIES=0"

echo Waiting for %URL%/health ...

:waitloop
set "CODE="
for /f %%c in ('curl.exe -s -o NUL -w "%%{http_code}" %URL%/health 2^>NUL') do set "CODE=%%c"
if "%CODE%"=="200" goto ready

set /a TRIES+=1
if %TRIES% GEQ %MAX_TRIES% (
    echo StoreOps did not report healthy within %MAX_TRIES% seconds.
    echo Check the server window for errors, then reload %URL%/docs manually.
    exit /b 1
)
rem 1-second delay. Deliberately not "timeout /t 1" -- if Git for Windows'
rem usr\bin is ahead of System32 on PATH, "timeout" resolves to its
rem coreutils version instead, which takes different arguments and errors
rem out. ping is effectively never shadowed the same way.
ping -n 2 127.0.0.1 >nul
goto waitloop

:ready
echo StoreOps is healthy. Opening the API docs in your browser ...
start "" "%URL%/docs"
endlocal
