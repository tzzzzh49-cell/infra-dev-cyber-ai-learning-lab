#!/usr/bin/env bash
set -euo pipefail

# Boucle principale Hermes + OpenClaw.
# Ce script est un squelette sûr pour exploitation manuelle sur VPS.
# Il ne contient aucun secret et n'affiche jamais le contenu des messages privés.

SERVICE_NAME="hermes-openclaw-loop"
SLEEP_SECONDS="${HERMES_OPENCLAW_LOOP_SLEEP:-10}"
EVENT_TIMEOUT_SECONDS="${HERMES_OPENCLAW_EVENT_TIMEOUT:-30}"
MAX_RESPONSE_CHARS="${HERMES_OPENCLAW_MAX_RESPONSE_CHARS:-800}"
RUNNING=true

log() {
  printf '[%s] %s\n' "${SERVICE_NAME}" "$*"
}

stop() {
  RUNNING=false
  log "arrêt demandé, fin de boucle après l'itération courante"
}

require_command() {
  local command_name="$1"
  if ! command -v "${command_name}" >/dev/null 2>&1; then
    log "commande manquante: ${command_name}"
    return 1
  fi
}

fetch_event() {
  # Commande indicative à adapter selon la version officielle OpenClaw.
  # La sortie peut contenir du contenu privé : elle n'est pas affichée.
  openclaw gateway next-event --timeout "${EVENT_TIMEOUT_SECONDS}" --format json
}

build_reply() {
  # Commande indicative à adapter selon la version officielle Hermes.
  # Hermes reçoit l'événement par stdin et doit produire une réponse courte.
  hermes request \
    --mcp openclaw \
    --max-chars "${MAX_RESPONSE_CHARS}" \
    --instruction "Réponds brièvement et n'expose aucun secret."
}

send_reply() {
  # Commande indicative à adapter selon la version officielle OpenClaw.
  # La réponse transite par stdin et n'est pas affichée par le script.
  openclaw gateway send-reply --stdin
}

trap stop INT TERM

require_command openclaw
require_command hermes

log "démarrage avec délai ${SLEEP_SECONDS}s et timeout événement ${EVENT_TIMEOUT_SECONDS}s"

while [[ "${RUNNING}" == "true" ]]; do
  event_file="$(mktemp)"
  reply_file="$(mktemp)"

  if fetch_event >"${event_file}" 2>/dev/null; then
    if [[ -s "${event_file}" ]]; then
      log "événement reçu; contenu privé masqué"
      if build_reply <"${event_file}" >"${reply_file}" 2>/dev/null; then
        if [[ -s "${reply_file}" ]]; then
          send_reply <"${reply_file}" >/dev/null 2>&1
          log "réponse envoyée; contenu privé masqué"
        else
          log "réponse vide ignorée"
        fi
      else
        log "échec Hermes; voir journaux techniques du service"
      fi
    else
      log "aucun événement"
    fi
  else
    log "OpenClaw n'a pas renvoyé d'événement exploitable"
  fi

  rm -f "${event_file}" "${reply_file}"

  if [[ "${RUNNING}" == "true" ]]; then
    sleep "${SLEEP_SECONDS}"
  fi
done

log "service arrêté proprement"
