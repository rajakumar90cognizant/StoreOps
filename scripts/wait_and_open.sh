#!/usr/bin/env bash
# Helper for start.sh: polls GET /health until it returns 200, then opens
# the Swagger UI (all APIs) in the default browser. Exits either way -- it
# does not manage the server's lifecycle.

set -uo pipefail

HOST="${1:-127.0.0.1}"
PORT="${2:-8010}"
URL="http://$HOST:$PORT"
MAX_TRIES=60
TRIES=0

echo "Waiting for $URL/health ..."

while true; do
    CODE="$(curl -s -o /dev/null -w '%{http_code}' "$URL/health" 2>/dev/null || echo "000")"
    if [ "$CODE" = "200" ]; then
        break
    fi
    TRIES=$((TRIES + 1))
    if [ "$TRIES" -ge "$MAX_TRIES" ]; then
        echo "StoreOps did not report healthy within ${MAX_TRIES}s." >&2
        echo "Check the server output for errors, then reload $URL/docs manually." >&2
        exit 1
    fi
    sleep 1
done

echo "StoreOps is healthy. Opening the API docs in your browser ..."

DOCS_URL="$URL/docs"
if command -v xdg-open >/dev/null 2>&1; then
    xdg-open "$DOCS_URL" >/dev/null 2>&1 &
elif command -v open >/dev/null 2>&1; then
    open "$DOCS_URL"
elif command -v cmd.exe >/dev/null 2>&1; then
    cmd.exe /c start "" "$DOCS_URL" >/dev/null 2>&1
elif command -v powershell.exe >/dev/null 2>&1; then
    powershell.exe -NoProfile -Command "Start-Process '$DOCS_URL'" >/dev/null 2>&1
else
    echo "Could not detect a way to open a browser automatically."
    echo "Open this URL manually: $DOCS_URL"
fi
