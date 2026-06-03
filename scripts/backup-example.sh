#!/usr/bin/env bash
set -euo pipefail

BACKUP_DIR="${BACKUP_DIR:-$HOME/backups}"
PROJECT_DIR="${PROJECT_DIR:-$HOME/hermes-openclaw}"
TIMESTAMP="$(date -u +%Y%m%d-%H%M%S)"
ARCHIVE_PATH="$BACKUP_DIR/hermes-openclaw-$TIMESTAMP.tar.gz"
CHECKSUM_PATH="$ARCHIVE_PATH.sha256"
SYSTEMD_UNIT="$HOME/.config/systemd/user/hermes-openclaw-loop.service"

log() {
    printf '[backup-example] %s\n' "$*"
}

add_if_exists() {
    local path="$1"
    local -n target_array="$2"

    if [ -e "$path" ]; then
        target_array+=("$path")
        log "inclus: $path"
    else
        log "absent, ignoré: $path"
    fi
}

mkdir -p "$BACKUP_DIR"
chmod 700 "$BACKUP_DIR"

paths_to_backup=()
add_if_exists "$HOME/.openclaw" paths_to_backup
add_if_exists "$HOME/.hermes" paths_to_backup
add_if_exists "$PROJECT_DIR" paths_to_backup
add_if_exists "$PROJECT_DIR/.env" paths_to_backup
add_if_exists "$SYSTEMD_UNIT" paths_to_backup

if [ "${#paths_to_backup[@]}" -eq 0 ]; then
    log "aucun chemin existant à sauvegarder"
    exit 1
fi

tar -czf "$ARCHIVE_PATH" --warning=no-file-changed "${paths_to_backup[@]}"
sha256sum "$ARCHIVE_PATH" > "$CHECKSUM_PATH"
chmod 600 "$ARCHIVE_PATH" "$CHECKSUM_PATH"

log "archive créée: $ARCHIVE_PATH"
log "checksum créé: $CHECKSUM_PATH"
log "chiffrement requis avant tout stockage externe: utiliser GPG ou age"
log "aucun transfert automatique n'a été effectué"
