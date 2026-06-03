#!/usr/bin/env bash
set -euo pipefail

SERVICE_NAME="${SERVICE_NAME:-hermes-openclaw-loop.service}"
STATUS=0

info() {
    printf '[INFO] %s\n' "$*"
}

ok() {
    printf '[OK] %s\n' "$*"
}

warn() {
    printf '[WARN] %s\n' "$*"
}

fail() {
    printf '[FAIL] %s\n' "$*"
    STATUS=1
}

check_command() {
    local command_name="$1"

    if command -v "$command_name" >/dev/null 2>&1; then
        ok "commande disponible: $command_name"
    else
        fail "commande introuvable: $command_name"
    fi
}

check_optional_command() {
    local description="$1"
    shift

    if "$@" >/tmp/hermes-openclaw-healthcheck.out 2>/tmp/hermes-openclaw-healthcheck.err; then
        ok "$description"
    else
        warn "$description indisponible ou en erreur"
        STATUS=1
    fi

    rm -f /tmp/hermes-openclaw-healthcheck.out /tmp/hermes-openclaw-healthcheck.err
}

info "vérification des commandes"
check_command openclaw
check_command hermes

if command -v openclaw >/dev/null 2>&1; then
    check_optional_command "openclaw gateway status" openclaw gateway status
fi

if command -v hermes >/dev/null 2>&1; then
    check_optional_command "hermes --version" hermes --version
fi

if command -v systemctl >/dev/null 2>&1 && systemctl --user list-units >/dev/null 2>&1; then
    if systemctl --user is-active --quiet "$SERVICE_NAME"; then
        ok "service utilisateur actif: $SERVICE_NAME"
    else
        warn "service utilisateur non actif: $SERVICE_NAME"
        STATUS=1
    fi
else
    warn "systemctl --user indisponible dans cet environnement"
fi

exit "$STATUS"
