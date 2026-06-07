#!/usr/bin/env bash
# shellcheck disable=SC2129

# Script de diagnostic local pour le projet infra-dev-cyber-ai-learning-lab.
# Objectif : observer l'état du système et générer un rapport Markdown.
# Ce script ne modifie rien sur la machine.

set -u

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPORT_DIR="$PROJECT_ROOT/outputs/reports"
TIMESTAMP="$(date +"%Y-%m-%d-%H%M%S")"
REPORT_FILE="$REPORT_DIR/diagnostic-$TIMESTAMP.md"
API_HEALTH_URL="${API_HEALTH_URL:-http://127.0.0.1:8000/health}"

mkdir -p "$REPORT_DIR"

DOCKER_STATUS="KO"
DOCKER_DETAILS="Docker non testé."

API_STATUS="KO"
API_DETAILS="API non testée."

check_docker() {
    if ! command -v docker >/dev/null 2>&1; then
        DOCKER_STATUS="KO"
        DOCKER_DETAILS="La commande docker est introuvable."
        return
    fi

    if timeout 5 docker ps >/tmp/diagnostic_docker.out 2>/tmp/diagnostic_docker.err; then
        DOCKER_STATUS="OK"
        DOCKER_DETAILS="Docker répond correctement à la commande docker ps."
    else
        DOCKER_STATUS="KO"
        DOCKER_DETAILS="$(cat /tmp/diagnostic_docker.err 2>/dev/null)"
    fi
}

check_api() {
    if ! command -v curl >/dev/null 2>&1; then
        API_STATUS="KO"
        API_DETAILS="La commande curl est introuvable."
        return
    fi

    local body_file
    local err_file
    local http_code

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

write_title() {
    echo "# Rapport de diagnostic local" > "$REPORT_FILE"
    echo "" >> "$REPORT_FILE"
    echo "Date du diagnostic : $(date)" >> "$REPORT_FILE"
    echo "" >> "$REPORT_FILE"
    echo "Projet : infra-dev-cyber-ai-learning-lab" >> "$REPORT_FILE"
    echo "" >> "$REPORT_FILE"
}

write_summary() {
    echo "## Synthèse rapide" >> "$REPORT_FILE"
    echo "" >> "$REPORT_FILE"
    echo "| Élément | Statut | Détail |" >> "$REPORT_FILE"
    echo "|---|---|---|" >> "$REPORT_FILE"
    echo "| Docker | $DOCKER_STATUS | $DOCKER_DETAILS |" >> "$REPORT_FILE"
    echo "| API /health | $API_STATUS | $API_DETAILS |" >> "$REPORT_FILE"
    echo "" >> "$REPORT_FILE"
}

write_section() {
    local title="$1"
    shift

    echo "" >> "$REPORT_FILE"
    echo "## $title" >> "$REPORT_FILE"
    echo "" >> "$REPORT_FILE"
    echo "Commande exécutée :" >> "$REPORT_FILE"
    echo "" >> "$REPORT_FILE"
    echo "    $*" >> "$REPORT_FILE"
    echo "" >> "$REPORT_FILE"
    echo "Résultat :" >> "$REPORT_FILE"
    echo "" >> "$REPORT_FILE"

    if command -v "$1" >/dev/null 2>&1; then
        "$@" >> "$REPORT_FILE" 2>&1 || true
    else
        echo "Commande introuvable : $1" >> "$REPORT_FILE"
    fi
}

write_health_check() {
    echo "" >> "$REPORT_FILE"
    echo "## Test détaillé de l'API locale" >> "$REPORT_FILE"
    echo "" >> "$REPORT_FILE"
    echo "URL testée :" >> "$REPORT_FILE"
    echo "" >> "$REPORT_FILE"
    echo "    $API_HEALTH_URL" >> "$REPORT_FILE"
    echo "" >> "$REPORT_FILE"
    echo "Résultat :" >> "$REPORT_FILE"
    echo "" >> "$REPORT_FILE"

    if command -v curl >/dev/null 2>&1; then
        curl -sS --max-time 3 "$API_HEALTH_URL" >> "$REPORT_FILE" 2>&1 || true
    else
        echo "Commande introuvable : curl" >> "$REPORT_FILE"
    fi

    echo "" >> "$REPORT_FILE"
}

write_conclusion() {
    echo "" >> "$REPORT_FILE"
    echo "## Conclusion" >> "$REPORT_FILE"
    echo "" >> "$REPORT_FILE"

    if [ "$DOCKER_STATUS" = "OK" ] && [ "$API_STATUS" = "OK" ]; then
        echo "Conclusion : Docker fonctionne et l'API répond correctement." >> "$REPORT_FILE"
    elif [ "$DOCKER_STATUS" = "OK" ] && [ "$API_STATUS" = "KO" ]; then
        echo "Conclusion : Docker fonctionne, mais l'API ne répond pas correctement." >> "$REPORT_FILE"
    elif [ "$DOCKER_STATUS" = "KO" ] && [ "$API_STATUS" = "OK" ]; then
        echo "Conclusion : l'API répond, mais Docker ne fonctionne pas correctement." >> "$REPORT_FILE"
    else
        echo "Conclusion : Docker et l'API semblent en erreur ou indisponibles." >> "$REPORT_FILE"
    fi

    echo "" >> "$REPORT_FILE"
    echo "Rapport généré ici :" >> "$REPORT_FILE"
    echo "" >> "$REPORT_FILE"
    echo "    $REPORT_FILE" >> "$REPORT_FILE"
}

check_docker
check_api

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
write_conclusion

echo "Diagnostic terminé."
echo "Docker : $DOCKER_STATUS"
echo "API : $API_STATUS"
echo "Rapport généré : $REPORT_FILE"
