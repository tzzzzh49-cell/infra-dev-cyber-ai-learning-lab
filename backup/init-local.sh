#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

RESTIC_REPOSITORY="${RESTIC_REPOSITORY:-$PROJECT_ROOT/outputs/backups/restic-local}"
RESTIC_PASSWORD_FILE="${RESTIC_PASSWORD_FILE:-}"

require_command() {
    local command_name="$1"

    if ! command -v "$command_name" >/dev/null 2>&1; then
        echo "ERREUR : commande introuvable : $command_name" >&2
        exit 1
    fi
}

ensure_local_repository() {
    case "$RESTIC_REPOSITORY" in
        *:*)
            echo "ERREUR : ce script initialise uniquement un dépôt Restic local." >&2
            echo "RESTIC_REPOSITORY ne doit pas utiliser de backend distant pour cette étape." >&2
            exit 2
            ;;
    esac
}

ensure_password_file() {
    if [ -z "$RESTIC_PASSWORD_FILE" ]; then
        echo "ERREUR : RESTIC_PASSWORD_FILE doit pointer vers un fichier privé hors Git." >&2
        exit 1
    fi

    if [ ! -f "$RESTIC_PASSWORD_FILE" ]; then
        echo "ERREUR : fichier de passphrase introuvable : $RESTIC_PASSWORD_FILE" >&2
        exit 1
    fi
}

require_command restic
ensure_local_repository
ensure_password_file

export RESTIC_REPOSITORY
export RESTIC_PASSWORD_FILE

mkdir -p "$RESTIC_REPOSITORY"

if [ -f "$RESTIC_REPOSITORY/config" ]; then
    restic snapshots >/dev/null
    echo "Dépôt Restic local déjà initialisé : $RESTIC_REPOSITORY"
else
    restic init
    echo "Dépôt Restic local initialisé : $RESTIC_REPOSITORY"
fi
