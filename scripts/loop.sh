#!/usr/bin/env bash
set -euo pipefail

# Boucle principale Hermes + OpenClaw.
# Ce script est volontairement conservateur : il ne journalise jamais le contenu
# des messages privés et évite toute commande shell destructive.

SLEEP_SECONDS="${HERMES_OPENCLAW_LOOP_SLEEP_SECONDS:-10}"
OPENCLAW_GATEWAY_URL="${OPENCLAW_GATEWAY_URL:-http://127.0.0.1:18789}"
HERMES_REQUEST_MODE="${HERMES_REQUEST_MODE:-request}"
STOP_REQUESTED=0

log() {
  printf '[hermes-openclaw-loop] %s\n' "$1"
}

on_stop() {
  STOP_REQUESTED=1
  log "arrêt demandé, fin propre après l'itération courante"
}

trap on_stop INT TERM

require_command() {
  local command_name="$1"
  if ! command -v "$command_name" >/dev/null 2>&1; then
    log "commande absente: $command_name"
    return 1
  fi
}

run_iteration() {
  # Étapes attendues :
  # 1. demander à Hermes de lire un événement OpenClaw via MCP ;
  # 2. lire uniquement le contexte autorisé ;
  # 3. rédiger une réponse courte ;
  # 4. envoyer la réponse via OpenClaw ;
  # 5. ne jamais afficher le contenu du message dans stdout/stderr.
  #
  # Les options exactes doivent être validées avec les versions officielles
  # d'Hermes et OpenClaw installées sur le VPS.
  hermes "$HERMES_REQUEST_MODE" \
    --mcp openclaw \
    --gateway-url "$OPENCLAW_GATEWAY_URL" \
    --instruction "Réponds brièvement via OpenClaw sans journaliser le message privé."
}

main() {
  require_command hermes
  require_command openclaw

  log "boucle démarrée avec délai ${SLEEP_SECONDS}s"

  while [ "$STOP_REQUESTED" -eq 0 ]; do
    if ! run_iteration >/dev/null 2>&1; then
      log "itération échouée, voir configuration Hermes/OpenClaw locale"
    else
      log "itération terminée"
    fi

    if [ "$STOP_REQUESTED" -eq 0 ]; then
      sleep "$SLEEP_SECONDS"
    fi
  done

  log "boucle arrêtée proprement"
}

main "$@"
