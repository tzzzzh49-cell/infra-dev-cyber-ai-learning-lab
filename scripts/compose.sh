#!/usr/bin/env bash

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

public_mode=false
starts_services=false
case "${COMPOSE_FILE:-}" in
    *compose.public.yaml*) public_mode=true ;;
esac
for argument in "$@"; do
    case "$argument" in
        *compose.public.yaml*) public_mode=true ;;
        up|start|restart|run) starts_services=true ;;
    esac
done

if [ "$public_mode" = true ] && [ "$starts_services" = true ]; then
    MTLS_DIR="${MTLS_DIR:-/etc/infra-lab/mtls}" \
        "$PROJECT_ROOT/scripts/check_mtls_files.sh"
fi

find_compose_cmd() {
    if docker compose version >/dev/null 2>&1; then
        if docker ps >/dev/null 2>&1; then
            COMPOSE_CMD=(docker compose)
            return
        fi

        echo "Erreur : Docker n'est pas accessible sans sudo." >&2
        echo "Reconnecte l'utilisateur au groupe docker, puis relance la commande." >&2
        exit 1
    fi

    if command -v docker-compose >/dev/null 2>&1 && docker-compose version >/dev/null 2>&1; then
        if docker ps >/dev/null 2>&1; then
            COMPOSE_CMD=(docker-compose)
            return
        fi

        echo "Erreur : Docker n'est pas accessible sans sudo." >&2
        echo "Reconnecte l'utilisateur au groupe docker, puis relance la commande." >&2
        exit 1
    fi

    echo "Erreur : Docker Compose est introuvable." >&2
    echo "Sur Fedora 44, lance : ./scripts/bootstrap_fedora44_vm.sh" >&2
    echo "Sur Ubuntu 26.04 Server, lance : ./scripts/bootstrap_ubuntu2604_server.sh" >&2
    exit 1
}

COMPOSE_CMD=()
find_compose_cmd

exec "${COMPOSE_CMD[@]}" "$@"
