#!/usr/bin/env bash
set -euo pipefail

BACKUP_DIR="${BACKUP_DIR:-${HOME}/backups}"
REPO_DIR="${REPO_DIR:-${HOME}/hermes-openclaw}"
TIMESTAMP="$(date -u '+%Y%m%dT%H%M%SZ')"
ARCHIVE_NAME="hermes-openclaw-backup-${TIMESTAMP}.tar.gz"
ARCHIVE_PATH="${BACKUP_DIR}/${ARCHIVE_NAME}"
CHECKSUM_PATH="${ARCHIVE_PATH}.sha256"
SYSTEMD_UNIT="${HOME}/.config/systemd/user/hermes-openclaw-loop.service"

printf '[INFO] Création du dossier de sauvegarde: %s\n' "${BACKUP_DIR}"
mkdir -p "${BACKUP_DIR}"
chmod 700 "${BACKUP_DIR}"

paths=()

add_if_exists() {
  local path="$1"

  if [[ -e "${path}" ]]; then
    paths+=("${path}")
    printf '[INFO] Inclus: %s\n' "${path}"
  else
    printf '[INFO] Ignoré car absent: %s\n' "${path}"
  fi
}

add_if_exists "${HOME}/.openclaw"
add_if_exists "${HOME}/.hermes"
add_if_exists "${REPO_DIR}"
add_if_exists "${REPO_DIR}/.env"
add_if_exists "${SYSTEMD_UNIT}"

if [[ "${#paths[@]}" -eq 0 ]]; then
  printf '[ERROR] Aucun chemin à sauvegarder.\n' >&2
  exit 1
fi

printf '[INFO] Création de l archive: %s\n' "${ARCHIVE_PATH}"
tar -czf "${ARCHIVE_PATH}" --absolute-names "${paths[@]}"

printf '[INFO] Création du checksum: %s\n' "${CHECKSUM_PATH}"
(
  cd "${BACKUP_DIR}"
  sha256sum "${ARCHIVE_NAME}" > "${ARCHIVE_NAME}.sha256"
)

chmod 600 "${ARCHIVE_PATH}" "${CHECKSUM_PATH}"

printf '[INFO] Sauvegarde locale terminée.\n'
printf '[WARN] Chiffrez cette archive avec GPG ou age avant tout stockage externe.\n'
printf '[WARN] Aucun transfert automatique n a été effectué.\n'
