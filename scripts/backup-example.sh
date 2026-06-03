#!/usr/bin/env bash
set -euo pipefail

BACKUP_DIR="${BACKUP_DIR:-${HOME}/backups}"
REPO_DIR="${REPO_DIR:-${HOME}/hermes-openclaw}"
TIMESTAMP="$(date -u +%Y%m%dT%H%M%SZ)"
ARCHIVE="${BACKUP_DIR}/hermes-openclaw-${TIMESTAMP}.tar.gz"
CHECKSUM="${ARCHIVE}.sha256"
SYSTEMD_UNIT="${HOME}/.config/systemd/user/hermes-openclaw-loop.service"

printf '[backup] création du dossier %s\n' "${BACKUP_DIR}"
mkdir -p "${BACKUP_DIR}"
chmod 700 "${BACKUP_DIR}"

paths=()
for candidate in \
  "${HOME}/.openclaw" \
  "${HOME}/.hermes" \
  "${REPO_DIR}" \
  "${REPO_DIR}/.env" \
  "${SYSTEMD_UNIT}"; do
  if [[ -e "${candidate}" ]]; then
    paths+=("${candidate}")
  fi
done

if [[ "${#paths[@]}" -eq 0 ]]; then
  printf '[backup] aucun chemin existant à sauvegarder\n' >&2
  exit 1
fi

printf '[backup] archive locale: %s\n' "${ARCHIVE}"
tar -czf "${ARCHIVE}" "${paths[@]}"
sha256sum "${ARCHIVE}" >"${CHECKSUM}"
chmod 600 "${ARCHIVE}" "${CHECKSUM}"

printf '[backup] checksum: %s\n' "${CHECKSUM}"
printf '[backup] aucun transfert automatique effectué\n'
printf '[backup] chiffrez cette archive avec GPG ou age avant tout stockage externe\n'
