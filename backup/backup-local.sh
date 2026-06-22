#!/usr/bin/env bash
set -euo pipefail
umask 077

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

RESTIC_REPOSITORY="${RESTIC_REPOSITORY:-$PROJECT_ROOT/outputs/backups/restic-local}"
RESTIC_PASSWORD_FILE="${RESTIC_PASSWORD_FILE:-}"
RESTIC_EXCLUDE_FILE="${RESTIC_EXCLUDE_FILE:-$PROJECT_ROOT/backup/restic-excludes.txt}"
RESTIC_BACKUP_PATHS="${RESTIC_BACKUP_PATHS:-}"

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
            echo "ERREUR : ce script sauvegarde uniquement vers un dépôt Restic local." >&2
            echo "Aucun backend S3 ou distant n'est configuré à cette étape." >&2
            exit 2
            ;;
    esac

    if [ ! -f "$RESTIC_REPOSITORY/config" ]; then
        echo "ERREUR : dépôt Restic non initialisé : $RESTIC_REPOSITORY" >&2
        echo "Exécuter d'abord : backup/init-local.sh" >&2
        exit 1
    fi
}

ensure_password_file() {
    local mode

    if [ -z "$RESTIC_PASSWORD_FILE" ]; then
        echo "ERREUR : RESTIC_PASSWORD_FILE doit pointer vers un fichier privé hors Git." >&2
        exit 1
    fi

    if [ ! -f "$RESTIC_PASSWORD_FILE" ]; then
        echo "ERREUR : fichier de passphrase introuvable : $RESTIC_PASSWORD_FILE" >&2
        exit 1
    fi

    if [ ! -r "$RESTIC_PASSWORD_FILE" ]; then
        echo "ERREUR : fichier de passphrase illisible : $RESTIC_PASSWORD_FILE" >&2
        exit 1
    fi

    mode="$(stat -c '%a' -- "$RESTIC_PASSWORD_FILE")"
    case "$mode" in
        400|600) ;;
        *)
            echo "ERREUR : le fichier de passphrase doit avoir le mode 0400 ou 0600, pas $mode." >&2
            exit 1
            ;;
    esac
}

select_backup_paths() {
    local candidate
    local candidates=(
        README.md
        ROADMAP.md
        AGENTS.md
        Makefile
        compose.yaml
        .env.example
        .env.vps.example
        .env.backup.example
        ansible
        app
        backup
        docs
        k8s
        lab
        openclaw
        scripts
        terraform
    )

    if [ -n "$RESTIC_BACKUP_PATHS" ]; then
        # shellcheck disable=SC2206
        SELECTED_BACKUP_PATHS=($RESTIC_BACKUP_PATHS)
        return
    fi

    SELECTED_BACKUP_PATHS=()
    for candidate in "${candidates[@]}"; do
        if [ -e "$candidate" ]; then
            SELECTED_BACKUP_PATHS+=("$candidate")
        fi
    done
}

require_command stat
require_command restic
ensure_local_repository
ensure_password_file

if [ ! -f "$RESTIC_EXCLUDE_FILE" ]; then
    echo "ERREUR : fichier d'exclusions introuvable : $RESTIC_EXCLUDE_FILE" >&2
    exit 1
fi

export RESTIC_REPOSITORY
export RESTIC_PASSWORD_FILE

restic snapshots >/dev/null
select_backup_paths

if [ "${#SELECTED_BACKUP_PATHS[@]}" -eq 0 ]; then
    echo "ERREUR : aucun chemin à sauvegarder." >&2
    exit 1
fi

restic backup \
    --exclude-file "$RESTIC_EXCLUDE_FILE" \
    "${SELECTED_BACKUP_PATHS[@]}"
