#!/usr/bin/env bash
set -euo pipefail

SERVICE_UNIT="hermes-openclaw-loop.service"
ERRORS=0

info() {
  printf '[healthcheck] %s\n' "$*"
}

fail() {
  printf '[healthcheck] ERREUR: %s\n' "$*" >&2
  ERRORS=$((ERRORS + 1))
}

check_command() {
  local command_name="$1"
  if command -v "${command_name}" >/dev/null 2>&1; then
    info "commande trouvée: ${command_name}"
  else
    fail "commande introuvable: ${command_name}"
  fi
}

check_command openclaw
check_command hermes

if command -v openclaw >/dev/null 2>&1; then
  if openclaw gateway status >/dev/null 2>&1; then
    info "OpenClaw gateway status: OK"
  else
    fail "OpenClaw gateway status indisponible ou non supporté"
  fi
fi

if command -v hermes >/dev/null 2>&1; then
  if hermes --version >/dev/null 2>&1; then
    info "Hermes --version: OK"
  else
    fail "Hermes --version indisponible"
  fi
fi

if command -v systemctl >/dev/null 2>&1; then
  if systemctl --user show-environment >/dev/null 2>&1; then
    if systemctl --user is-active --quiet "${SERVICE_UNIT}"; then
      info "service utilisateur actif: ${SERVICE_UNIT}"
    else
      fail "service utilisateur inactif: ${SERVICE_UNIT}"
    fi
  else
    info "systemctl --user non disponible dans cette session; vérification ignorée"
  fi
else
  info "systemctl introuvable; vérification systemd ignorée"
fi

if [[ "${ERRORS}" -eq 0 ]]; then
  info "OK"
  exit 0
fi

fail "${ERRORS} vérification(s) en échec"
exit 1
