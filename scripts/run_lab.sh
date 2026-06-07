#!/usr/bin/env bash

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUNTIME_DIR="$PROJECT_ROOT/.runtime"
APP_URL_FILE="$RUNTIME_DIR/app_url"
APP_HOST="${APP_HOST:-127.0.0.1}"
APP_PORT_WAS_SET=""
if [ -n "${APP_PORT:-}" ]; then
    APP_PORT_WAS_SET="1"
fi
APP_PORT="${APP_PORT:-8000}"

port_available() {
    local host="$1"
    local port="$2"

    python3 - "$host" "$port" <<'PY'
import socket
import sys

host = sys.argv[1]
port = int(sys.argv[2])

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        sock.bind((host, port))
    except OSError:
        sys.exit(1)
PY
}

if ! port_available "$APP_HOST" "$APP_PORT"; then
    if [ -n "$APP_PORT_WAS_SET" ]; then
        echo "Erreur : le port $APP_HOST:$APP_PORT est deja utilise." >&2
        echo "Choisis un autre port, par exemple : APP_PORT=8001 make run" >&2
        exit 1
    fi

    for candidate_port in $(seq 8001 8020); do
        if port_available "$APP_HOST" "$candidate_port"; then
            APP_PORT="$candidate_port"
            echo "Port 8000 occupe, utilisation de $APP_HOST:$APP_PORT."
            break
        fi
    done
fi

if ! port_available "$APP_HOST" "$APP_PORT"; then
    echo "Erreur : aucun port libre trouve entre 8000 et 8020." >&2
    exit 1
fi

HEALTH_HOST="$APP_HOST"
if [ "$HEALTH_HOST" = "0.0.0.0" ]; then
    HEALTH_HOST="127.0.0.1"
fi

export APP_HOST APP_PORT
APP_URL="http://$HEALTH_HOST:$APP_PORT"
HEALTH_URL="${HEALTH_URL:-$APP_URL/health}"

"$PROJECT_ROOT/scripts/compose.sh" -f "$PROJECT_ROOT/compose.yaml" up -d --build

echo "Attente de l'API sur $HEALTH_URL ..."

for attempt in $(seq 1 30); do
    if curl -fsS --max-time 2 "$HEALTH_URL" >/dev/null 2>&1; then
        mkdir -p "$RUNTIME_DIR"
        printf '%s\n' "$APP_URL" > "$APP_URL_FILE"
        echo "API disponible : $HEALTH_URL"
        exit 0
    fi

    if [ "$attempt" = "30" ]; then
        break
    fi

    sleep 1
done

echo "Erreur : l'API ne repond pas apres 30 secondes." >&2
"$PROJECT_ROOT/scripts/compose.sh" -f "$PROJECT_ROOT/compose.yaml" ps >&2 || true
exit 1
