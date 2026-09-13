#!/usr/bin/env bash
# StoreOps local startup (Linux/macOS/Git Bash).
# Creates/updates the venv, installs deps, starts the API on port 8010,
# waits for /health, then opens the Swagger UI (all endpoints) in the
# default browser. Ctrl+C (or closing this terminal) stops the server --
# uvicorn runs via `exec`, replacing this shell, so it receives Ctrl+C and
# terminal-close signals directly rather than being a detached child.
#
# Self-healing: if a previous run left a stale process still bound to the
# port (crashed, force-killed terminal, etc.), this script stops it before
# starting a new one -- that's what avoids "OSError: [Errno 98] Address
# already in use" on the next run. Run ./stop.sh at any time to explicitly
# stop whatever is currently listening on the port.

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

HOST="127.0.0.1"
PORT="8010"
VENV_DIR=".venv"

echo "=== StoreOps startup ==="
echo "Project root: $ROOT_DIR"

# --- locate a Python interpreter ---
PY_CMD=""
if command -v python3 >/dev/null 2>&1; then
    PY_CMD="python3"
elif command -v python >/dev/null 2>&1; then
    PY_CMD="python"
else
    echo "ERROR: No Python interpreter found on PATH. Install Python 3.11+ and re-run." >&2
    exit 1
fi

# --- locate (or create) the venv's activate script. A venv created by
#     Windows Python uses Scripts/activate; POSIX Python uses bin/activate --
#     support both so this also works from Git Bash against a Windows venv.
find_activate() {
    if [ -f "$VENV_DIR/bin/activate" ]; then
        echo "$VENV_DIR/bin/activate"
    elif [ -f "$VENV_DIR/Scripts/activate" ]; then
        echo "$VENV_DIR/Scripts/activate"
    fi
}

ACTIVATE="$(find_activate || true)"
if [ -z "$ACTIVATE" ]; then
    echo "Creating virtual environment in \"$VENV_DIR\" ..."
    "$PY_CMD" -m venv "$VENV_DIR"
    ACTIVATE="$(find_activate || true)"
    if [ -z "$ACTIVATE" ]; then
        echo "ERROR: Virtual environment was created but no activate script was found." >&2
        exit 1
    fi
else
    echo "Using existing virtual environment in \"$VENV_DIR\"."
fi

# shellcheck disable=SC1090
source "$ACTIVATE"

echo "Installing/updating dependencies ..."
python -m pip install --upgrade pip --quiet
pip install -r requirements.txt --quiet
pip install -e . --quiet
echo "Dependencies ready."

# --- self-heal: stop whatever is already bound to HOST:PORT, if anything
#     (a stale process from a previous run that wasn't shut down cleanly) ---
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

STALE_PID="$(find_pid_on_port || true)"
if [ -n "${STALE_PID:-}" ]; then
    echo "Port $PORT is already in use by process $STALE_PID -- likely a"
    echo "leftover from a previous run that wasn't shut down cleanly. Stopping it ..."
    if command -v taskkill.exe >/dev/null 2>&1; then
        taskkill.exe /F /PID "$STALE_PID" >/dev/null 2>&1 || true
    else
        kill -9 "$STALE_PID" 2>/dev/null || true
    fi
    sleep 1
fi

# --- background helper: waits for /health, then opens the API docs ---
"$ROOT_DIR/scripts/wait_and_open.sh" "$HOST" "$PORT" &
disown 2>/dev/null || true

echo
echo "Starting StoreOps on http://$HOST:$PORT"
echo "All APIs are documented at http://$HOST:$PORT/docs -- it opens"
echo "automatically once /health reports ready."
echo "Press Ctrl+C to stop the server (or run ./stop.sh from another terminal)."
echo

exec uvicorn app.main:app --host "$HOST" --port "$PORT"
