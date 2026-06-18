#!/usr/bin/env bash

set -euo pipefail

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
