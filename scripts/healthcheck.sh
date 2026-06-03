#!/usr/bin/env bash
set -euo pipefail

STATUS=0

info() {
  printf '[INFO] %s\n' "$1"
}

warn() {
  printf '[WARN] %s\n' "$1"
}

fail() {
  printf '[FAIL] %s\n' "$1"
  STATUS=1
}

check_command() {
  local command_name="$1"
  if command -v "$command_name" >/dev/null 2>&1; then
    info "commande disponible: $command_name"
  else
    fail "commande absente: $command_name"
  fi
}

check_openclaw() {
  if ! command -v openclaw >/dev/null 2>&1; then
    return
  fi

  if openclaw --version >/dev/null 2>&1; then
    info "openclaw --version OK"
  else
    warn "openclaw --version non disponible ou en erreur"
  fi

  if openclaw gateway status >/dev/null 2>&1; then
    info "openclaw gateway status OK"
  else
    warn "openclaw gateway status non disponible ou gateway arrêtée"
  fi
}

check_hermes() {
  if ! command -v hermes >/dev/null 2>&1; then
    return
  fi

  if hermes --version >/dev/null 2>&1; then
    info "hermes --version OK"
  else
    warn "hermes --version non disponible ou en erreur"
  fi
}

check_systemd_user() {
  if ! command -v systemctl >/dev/null 2>&1; then
    warn "systemctl absent, vérification systemd utilisateur ignorée"
    return
  fi

  if systemctl --user show-environment >/dev/null 2>&1; then
    info "systemctl --user disponible"
    if systemctl --user is-active --quiet hermes-openclaw-loop.service; then
      info "hermes-openclaw-loop.service actif"
    else
      warn "hermes-openclaw-loop.service inactif ou non installé"
    fi
  else
    warn "systemctl --user indisponible dans cette session"
  fi
}

main() {
  check_command openclaw
  check_command hermes
  check_openclaw
  check_hermes
  check_systemd_user

  if [ "$STATUS" -eq 0 ]; then
    info "healthcheck terminé sans erreur bloquante"
  else
    fail "healthcheck terminé avec erreur bloquante"
  fi

  return "$STATUS"
}

main "$@"
