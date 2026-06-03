#!/usr/bin/env bash
set -euo pipefail


PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
HEALTH_URL="${HEALTH_URL:-http://127.0.0.1:8000/health}"

"$PROJECT_ROOT/scripts/compose.sh" -f "$PROJECT_ROOT/compose.yaml" up -d --build

echo "Attente de l'API sur $HEALTH_URL ..."

for attempt in $(seq 1 30); do
    if curl -fsS --max-time 2 "$HEALTH_URL" >/dev/null 2>&1; then
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
