#!/usr/bin/env bash
set -euo pipefail

BACKUP_DIR="${BACKUP_DIR:-$HOME/backups}"
REPO_DIR="${REPO_DIR:-$HOME/hermes-openclaw}"
TIMESTAMP="$(date +%Y%m%d-%H%M%S)"
ARCHIVE="$BACKUP_DIR/hermes-openclaw-$TIMESTAMP.tar.gz"
CHECKSUM="$ARCHIVE.sha256"
SYSTEMD_UNIT="$HOME/.config/systemd/user/hermes-openclaw-loop.service"

log() {
  printf '[backup-example] %s\n' "$1"
}

add_if_exists() {
  local path="$1"
  local -n output_array="$2"

  if [ -e "$path" ]; then
    output_array+=("$path")
    log "inclus: $path"
  else
    log "ignoré, absent: $path"
  fi
}

main() {
  local paths=()

  mkdir -p "$BACKUP_DIR"
  chmod 700 "$BACKUP_DIR"

  add_if_exists "$HOME/.openclaw" paths
  add_if_exists "$HOME/.hermes" paths
  add_if_exists "$REPO_DIR" paths
  add_if_exists "$REPO_DIR/.env" paths
  add_if_exists "$SYSTEMD_UNIT" paths

  if [ "${#paths[@]}" -eq 0 ]; then
    log "aucun chemin à sauvegarder"
    return 1
  fi

  tar -czf "$ARCHIVE" "${paths[@]}"
  sha256sum "$ARCHIVE" > "$CHECKSUM"
  chmod 600 "$ARCHIVE" "$CHECKSUM"

  log "archive créée: $ARCHIVE"
  log "checksum créé: $CHECKSUM"
  log "aucun transfert automatique effectué"
  log "chiffrer l'archive avec GPG ou age avant tout stockage externe"
}

main "$@"
