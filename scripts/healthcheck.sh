#!/usr/bin/env bash
set -euo pipefail

SERVICE_NAME="hermes-openclaw-loop.service"
FAILURES=0

info() {
  printf '[INFO] %s\n' "$*"
}

warn() {
  printf '[WARN] %s\n' "$*"
}

fail() {
  printf '[FAIL] %s\n' "$*"
  FAILURES=$((FAILURES + 1))
}

check_command() {
  local command_name="$1"

  if command -v "${command_name}" >/dev/null 2>&1; then
    info "Commande disponible: ${command_name} ($(command -v "${command_name}"))"
  else
    fail "Commande indisponible: ${command_name}"
  fi
}

check_openclaw() {
  if ! command -v openclaw >/dev/null 2>&1; then
    return
  fi

  if openclaw gateway status >/dev/null 2>&1; then
    info "OpenClaw gateway status OK."
  else
    warn "openclaw gateway status indisponible ou gateway non démarrée. Vérifiez la commande officielle de votre version."
  fi
}

check_hermes() {
  if ! command -v hermes >/dev/null 2>&1; then
    return
  fi

  if hermes --version >/dev/null 2>&1; then
    info "Hermes --version OK."
  else
    fail "hermes --version retourne une erreur."
  fi
}

check_systemd_user() {
  if ! command -v systemctl >/dev/null 2>&1; then
    warn "systemctl indisponible. Vérification systemd ignorée."
    return
  fi

  if ! systemctl --user show-environment >/dev/null 2>&1; then
    warn "systemctl --user indisponible dans cette session. Vérification systemd ignorée."
    return
  fi

  if systemctl --user is-active --quiet "${SERVICE_NAME}"; then
    info "Service utilisateur actif: ${SERVICE_NAME}"
  else
    fail "Service utilisateur inactif ou absent: ${SERVICE_NAME}"
  fi
}

check_command openclaw
check_command hermes
check_openclaw
check_hermes
check_systemd_user

if [[ "${FAILURES}" -eq 0 ]]; then
  info "Healthcheck terminé sans échec bloquant."
  exit 0
fi

fail "Healthcheck terminé avec ${FAILURES} échec(s)."
exit 1
