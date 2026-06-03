#!/usr/bin/env bash
set -euo pipefail

# Boucle principale Hermes + OpenClaw.
# Ce script est volontairement prudent : il ne journalise pas les messages privés
# et n'exécute aucune commande destructive.

LOOP_INTERVAL_SECONDS="${LOOP_INTERVAL_SECONDS:-15}"
OPENCLAW_GATEWAY_URL="${OPENCLAW_GATEWAY_URL:-http://127.0.0.1:18789}"
HERMES_REQUEST_MODE="${HERMES_REQUEST_MODE:-request}"
STOP_REQUESTED=0

log() {
  printf '[%s] %s\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ')" "$*"
}

request_stop() {
  STOP_REQUESTED=1
  log "Signal reçu, arrêt propre demandé."
}

require_command() {
  local command_name="$1"

  if ! command -v "${command_name}" >/dev/null 2>&1; then
    log "Commande manquante: ${command_name}"
    return 1
  fi
}

run_iteration() {
  # Les commandes exactes OpenClaw/Hermes peuvent varier selon les versions.
  # Le prompt demande à Hermes d'utiliser MCP pour lire un événement, rédiger
  # une réponse courte et l'envoyer via OpenClaw, sans afficher le contenu privé.
  local prompt

  prompt="Utilise MCP pour vérifier OpenClaw Gateway (${OPENCLAW_GATEWAY_URL}). Si un événement utilisateur est en attente, lis uniquement le contexte nécessaire, rédige une réponse courte et envoie-la via OpenClaw. Ne journalise aucun message privé. Si aucun événement n'est disponible, termine sans action."

  hermes "${HERMES_REQUEST_MODE}" "${prompt}"
}

trap request_stop INT TERM

require_command hermes
require_command openclaw

log "Démarrage de la boucle Hermes + OpenClaw. Intervalle: ${LOOP_INTERVAL_SECONDS}s."

while [[ "${STOP_REQUESTED}" -eq 0 ]]; do
  if run_iteration; then
    log "Itération terminée."
  else
    log "Itération en erreur. Nouvelle tentative après délai."
  fi

  if [[ "${STOP_REQUESTED}" -eq 1 ]]; then
    break
  fi

  sleep "${LOOP_INTERVAL_SECONDS}"
done

log "Boucle arrêtée proprement."
