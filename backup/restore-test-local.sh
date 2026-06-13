#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

TIMESTAMP="$(date +"%Y-%m-%d-%H%M%S")"
RESTIC_REPOSITORY="${RESTIC_REPOSITORY:-$PROJECT_ROOT/outputs/backups/restic-local}"
RESTIC_PASSWORD_FILE="${RESTIC_PASSWORD_FILE:-}"
RESTIC_RESTORE_TARGET="${RESTIC_RESTORE_TARGET:-/tmp/infra-dev-cyber-ai-learning-lab-restic-restore-test-$TIMESTAMP}"

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
            echo "ERREUR : ce script teste uniquement une restauration locale." >&2
            echo "Aucun backend S3 ou distant n'est configuré à cette étape." >&2
            exit 2
            ;;
    esac

    if [ ! -f "$RESTIC_REPOSITORY/config" ]; then
        echo "ERREUR : dépôt Restic non initialisé : $RESTIC_REPOSITORY" >&2
        exit 1
    fi
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

ensure_restore_target() {
    case "$RESTIC_RESTORE_TARGET" in
        /tmp/*)
            ;;
        *)
            echo "ERREUR : RESTIC_RESTORE_TARGET doit rester sous /tmp pour ce test." >&2
            exit 2
            ;;
    esac

    if [ -e "$RESTIC_RESTORE_TARGET" ]; then
        echo "ERREUR : cible de restauration déjà existante : $RESTIC_RESTORE_TARGET" >&2
        exit 1
    fi
}

require_command restic
ensure_local_repository
ensure_password_file
ensure_restore_target

export RESTIC_REPOSITORY
export RESTIC_PASSWORD_FILE

restic snapshots >/dev/null
restic restore latest --target "$RESTIC_RESTORE_TARGET"

echo "Restauration de test terminée : $RESTIC_RESTORE_TARGET"
find "$RESTIC_RESTORE_TARGET" -maxdepth 2 -type f | sort | head -n 20
