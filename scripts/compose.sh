#!/usr/bin/env bash
set -euo pipefail


find_compose_cmd() {
    if docker compose version >/dev/null 2>&1; then
        if docker ps >/dev/null 2>&1; then
            COMPOSE_CMD=(docker compose)
            return
        fi

        if command -v sudo >/dev/null 2>&1 && sudo -n docker ps >/dev/null 2>&1; then
            COMPOSE_CMD=(sudo docker compose)
            return
        fi

        COMPOSE_CMD=(docker compose)
        return
    fi

    if command -v docker-compose >/dev/null 2>&1 && docker-compose version >/dev/null 2>&1; then
        if docker ps >/dev/null 2>&1; then
            COMPOSE_CMD=(docker-compose)
            return
        fi

        if command -v sudo >/dev/null 2>&1 && sudo -n docker ps >/dev/null 2>&1; then
            COMPOSE_CMD=(sudo docker-compose)
            return
        fi

        COMPOSE_CMD=(docker-compose)
        return
    fi

    echo "Erreur : Docker Compose est introuvable." >&2
    echo "Sur Fedora 44, lance : ./scripts/bootstrap_fedora44_vm.sh" >&2
    echo "Sur Ubuntu 24.04, lance : ./scripts/bootstrap_ubuntu2404.sh" >&2
    exit 1
}

COMPOSE_CMD=()
find_compose_cmd

exec "${COMPOSE_CMD[@]}" "$@"
