#!/usr/bin/env bash

# Script de diagnostic local pour le projet infra-dev-cyber-ai-learning-lab.
# Objectif : observer l'état du système et générer un rapport Markdown.
# Ce script ne modifie rien sur la machine.

set -u

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPORT_DIR="$PROJECT_ROOT/outputs/reports"
TIMESTAMP="$(date +"%Y-%m-%d-%H%M%S")"
REPORT_FILE="$REPORT_DIR/diagnostic-$TIMESTAMP.md"
DIAG_JSON_FILE="$REPORT_DIR/diagnostic-api-$TIMESTAMP.json"
API_HEALTH_URL="${API_HEALTH_URL:-http://127.0.0.1:8000/health}"
API_DIAG_URL="${API_DIAG_URL:-http://127.0.0.1:8000/diag}"

mkdir -p "$REPORT_DIR"

DOCKER_STATUS="KO"
DOCKER_DETAILS="Docker non testé."

API_STATUS="KO"
API_DETAILS="API non testée."
API_DIAG_STATUS="KO"
API_DIAG_DETAILS="Diagnostic API non testé."

check_docker() {
    local docker_out
    local docker_err

    if ! command -v docker >/dev/null 2>&1; then
        DOCKER_STATUS="KO"
        DOCKER_DETAILS="La commande docker est introuvable."
        return
    fi

    docker_out="$(mktemp)"
    docker_err="$(mktemp)"

    if timeout 5 docker ps >"$docker_out" 2>"$docker_err"; then
        DOCKER_STATUS="OK"
        DOCKER_DETAILS="Docker répond correctement à la commande docker ps."
    else
        DOCKER_STATUS="KO"
        DOCKER_DETAILS="$(cat "$docker_err")"
    fi

    rm -f "$docker_out" "$docker_err"
}

check_api() {
    local body_file
    local err_file
    local http_code

    if ! command -v curl >/dev/null 2>&1; then
        API_STATUS="KO"
        API_DETAILS="La commande curl est introuvable."
        return
    fi

    body_file="$(mktemp)"
    err_file="$(mktemp)"

    http_code="$(curl -sS --max-time 3 -o "$body_file" -w "%{http_code}" "$API_HEALTH_URL" 2>"$err_file" || true)"

    if [ "$http_code" = "200" ]; then
        API_STATUS="OK"
        API_DETAILS="L'API répond correctement avec le code HTTP 200."
    else
        API_STATUS="KO"
        API_DETAILS="L'API ne répond pas correctement. Code HTTP : $http_code. Erreur : $(cat "$err_file")"
    fi

    rm -f "$body_file" "$err_file"
}

fetch_api_diagnostic() {
    local err_file
    local http_code

    if ! command -v curl >/dev/null 2>&1; then
        API_DIAG_STATUS="KO"
        API_DIAG_DETAILS="La commande curl est introuvable ; aucun JSON /diag sauvegardé."
        return
    fi

    err_file="$(mktemp)"
    http_code="$(curl -sS --max-time 3 -o "$DIAG_JSON_FILE" -w "%{http_code}" "$API_DIAG_URL" 2>"$err_file" || true)"

    if [ "$http_code" = "200" ]; then
        API_DIAG_STATUS="OK"
        API_DIAG_DETAILS="Réponse /diag sauvegardée dans $DIAG_JSON_FILE."
    else
        API_DIAG_STATUS="KO"
        API_DIAG_DETAILS="/diag indisponible ou non démarré. Code HTTP : $http_code. Erreur : $(cat "$err_file")"
        rm -f "$DIAG_JSON_FILE"
    fi

    rm -f "$err_file"
}

write_title() {
    {
        echo "# Rapport de diagnostic local"
        echo ""
        echo "Date du diagnostic : $(date)"
        echo ""
        echo "Projet : infra-dev-cyber-ai-learning-lab"
        echo ""
    } >"$REPORT_FILE"
}

write_summary() {
    {
        echo "## Synthèse rapide"
        echo ""
        echo "| Élément | Statut | Détail |"
        echo "|---|---|---|"
        echo "| Docker | $DOCKER_STATUS | $DOCKER_DETAILS |"
        echo "| API /health | $API_STATUS | $API_DETAILS |"
        echo "| API /diag JSON | $API_DIAG_STATUS | $API_DIAG_DETAILS |"
        echo ""
    } >>"$REPORT_FILE"
}

write_section() {
    local title="$1"
    shift

    {
        echo ""
        echo "## $title"
        echo ""
        echo "Commande exécutée :"
        echo ""
        echo "    $*"
        echo ""
        echo "Résultat :"
        echo ""
    } >>"$REPORT_FILE"

    if command -v "$1" >/dev/null 2>&1; then
        "$@" >>"$REPORT_FILE" 2>&1 || true
    else
        echo "Commande introuvable : $1" >>"$REPORT_FILE"
    fi
}

write_health_check() {
    {
        echo ""
        echo "## Test détaillé de l'API locale"
        echo ""
        echo "URL testée :"
        echo ""
        echo "    $API_HEALTH_URL"
        echo ""
        echo "Résultat :"
        echo ""
    } >>"$REPORT_FILE"

    if command -v curl >/dev/null 2>&1; then
        curl -sS --max-time 3 "$API_HEALTH_URL" >>"$REPORT_FILE" 2>&1 || true
    else
        echo "Commande introuvable : curl" >>"$REPORT_FILE"
    fi

    echo "" >>"$REPORT_FILE"
}

write_diag_json_section() {
    {
        echo ""
        echo "## Export JSON API /diag"
        echo ""
        echo "URL testée :"
        echo ""
        echo "    $API_DIAG_URL"
        echo ""
        echo "Statut : $API_DIAG_STATUS"
        echo ""
        echo "Détail : $API_DIAG_DETAILS"
        echo ""
    } >>"$REPORT_FILE"

    if [ "$API_DIAG_STATUS" = "OK" ]; then
        {
            echo "JSON sauvegardé ici :"
            echo ""
            echo "    $DIAG_JSON_FILE"
            echo ""
        } >>"$REPORT_FILE"
    fi
}

write_conclusion() {
    {
        echo ""
        echo "## Conclusion"
        echo ""
    } >>"$REPORT_FILE"

    if [ "$DOCKER_STATUS" = "OK" ] && [ "$API_STATUS" = "OK" ]; then
        echo "Conclusion : Docker fonctionne et l'API répond correctement." >>"$REPORT_FILE"
    elif [ "$DOCKER_STATUS" = "OK" ] && [ "$API_STATUS" = "KO" ]; then
        echo "Conclusion : Docker fonctionne, mais l'API ne répond pas correctement." >>"$REPORT_FILE"
    elif [ "$DOCKER_STATUS" = "KO" ] && [ "$API_STATUS" = "OK" ]; then
        echo "Conclusion : l'API répond, mais Docker ne fonctionne pas correctement." >>"$REPORT_FILE"
    else
        echo "Conclusion : Docker et l'API semblent en erreur ou indisponibles." >>"$REPORT_FILE"
    fi

    {
        echo ""
        echo "Rapport généré ici :"
        echo ""
        echo "    $REPORT_FILE"
    } >>"$REPORT_FILE"
}

check_docker
check_api
fetch_api_diagnostic

write_title
write_summary

write_section "Nom de la machine" hostname
write_section "Informations système" uname -a
write_section "Interfaces réseau" ip a
write_section "Routes réseau" ip route
write_section "Ports ouverts" ss -tulpn
write_section "Espace disque" df -h
write_section "Mémoire" free -h
write_section "Conteneurs Docker" timeout 5 docker ps

write_health_check
write_diag_json_section
write_conclusion

echo "Diagnostic terminé."
echo "Docker : $DOCKER_STATUS"
echo "API : $API_STATUS"
echo "API /diag JSON : $API_DIAG_STATUS"
echo "Rapport généré : $REPORT_FILE"
if [ "$API_DIAG_STATUS" = "OK" ]; then
    echo "JSON API sauvegardé : $DIAG_JSON_FILE"
fi
