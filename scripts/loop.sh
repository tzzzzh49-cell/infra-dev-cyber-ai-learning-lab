#!/usr/bin/env bash
set -euo pipefail

# Boucle d'orchestration Hermes + OpenClaw.
# Ce script est volontairement conservateur : il ne lance aucune commande
# destructive et ne journalise aucun contenu de message privé.

LOOP_INTERVAL_SECONDS="${LOOP_INTERVAL_SECONDS:-30}"
HERMES_COMMAND="${HERMES_COMMAND:-hermes}"
OPENCLAW_COMMAND="${OPENCLAW_COMMAND:-openclaw}"
STOP_REQUESTED=0

log() {
    printf '[hermes-openclaw-loop] %s\n' "$*"
}

request_stop() {
    STOP_REQUESTED=1
    log "arrêt demandé, fin de boucle après l'itération courante"
}

require_command() {
    local command_name="$1"

    if ! command -v "$command_name" >/dev/null 2>&1; then
        log "commande introuvable: $command_name"
        return 1
    fi
}

run_iteration() {
    # Rôle attendu en production :
    # 1. attendre ou récupérer un événement OpenClaw ;
    # 2. demander à Hermes de lire le contexte via MCP ;
    # 3. produire une réponse courte ;
    # 4. envoyer la réponse via OpenClaw ;
    # 5. ne jamais afficher le contenu privé dans les logs.
    #
    # La commande exacte dépend des versions officielles OpenClaw/Hermes.
    # Elle est donc encapsulée dans une invocation illustrative et non fragile.
    "$HERMES_COMMAND" run --once --mcp openclaw --instruction \
        "Traite le prochain événement OpenClaw disponible via MCP. Réponds brièvement. Ne journalise pas le contenu privé."
}

trap request_stop INT TERM

if ! [[ "$LOOP_INTERVAL_SECONDS" =~ ^[0-9]+$ ]]; then
    log "LOOP_INTERVAL_SECONDS doit être un entier positif"
    exit 2
fi

require_command "$OPENCLAW_COMMAND"
require_command "$HERMES_COMMAND"

log "démarrage de la boucle, délai=${LOOP_INTERVAL_SECONDS}s"

while [ "$STOP_REQUESTED" -eq 0 ]; do
    if run_iteration; then
        log "itération terminée"
    else
        log "itération en erreur; consulter la configuration OpenClaw, MCP et Hermes"
    fi

    if [ "$STOP_REQUESTED" -eq 1 ]; then
        break
    fi

    sleep "$LOOP_INTERVAL_SECONDS"
done

log "boucle arrêtée proprement"
