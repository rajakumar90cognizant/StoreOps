#!/usr/bin/env bash
# Stops whatever is currently listening on StoreOps' port (default 8010),
# regardless of how it was started or whether its terminal is still open.
# Usage: ./stop.sh [port]

set -uo pipefail

PORT="${1:-8010}"

# Prevent Git Bash/MSYS from mangling "/F" and "/PID" into filesystem paths
# when we shell out to the native Windows taskkill.exe below.
export MSYS_NO_PATHCONV=1

find_pid_on_port() {
    if command -v lsof >/dev/null 2>&1; then
        lsof -ti "tcp:$PORT" 2>/dev/null | head -n 1
        return
    fi
    if command -v fuser >/dev/null 2>&1; then
        fuser "$PORT/tcp" 2>/dev/null | awk '{print $1}'
        return
    fi
    # Neither lsof nor fuser exists on plain Git Bash for Windows -- fall
    # back to the same PowerShell lookup start.bat/stop.bat use.
    if command -v powershell.exe >/dev/null 2>&1; then
        powershell.exe -NoProfile -Command \
            "(Get-NetTCPConnection -LocalPort $PORT -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1 -ExpandProperty OwningProcess)" \
            2>/dev/null | tr -d '\r'
    fi
}

stop_pid() {
    local pid="$1"
    if command -v taskkill.exe >/dev/null 2>&1; then
        taskkill.exe /F /PID "$pid" >/dev/null 2>&1
    else
        kill -9 "$pid" 2>/dev/null
    fi
}

TARGET_PID="$(find_pid_on_port || true)"

if [ -z "${TARGET_PID:-}" ]; then
    echo "Nothing is listening on port $PORT. Nothing to stop."
    exit 0
fi

echo "Stopping process $TARGET_PID listening on port $PORT ..."
if stop_pid "$TARGET_PID"; then
    echo "Done."
else
    echo "Could not stop process $TARGET_PID. It may require elevated privileges," >&2
    echo "or may have already exited." >&2
    exit 1
fi
