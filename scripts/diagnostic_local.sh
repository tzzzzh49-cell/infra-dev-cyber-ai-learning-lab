#!/usr/bin/env bash
# shellcheck disable=SC2129

# Script de diagnostic local pour le projet infra-dev-cyber-ai-learning-lab.
# Objectif : observer l'état du système et générer un rapport Markdown.
# Ce script ne modifie rien sur la machine.

set -u
umask 077

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPORT_DIR="$PROJECT_ROOT/outputs/reports"
TIMESTAMP="$(date +"%Y-%m-%d-%H%M%S")"
REPORT_FILE="$REPORT_DIR/diagnostic-$TIMESTAMP.md"
API_HEALTH_URL="${API_HEALTH_URL:-http://127.0.0.1:8000/health}"
API_DIAG_URL="${API_DIAG_URL:-http://127.0.0.1:8000/diag}"
DIAG_JSON_FILE="$REPORT_DIR/diagnostic-api-$TIMESTAMP.json"
TEMP_DIR="$(mktemp -d /tmp/infra-dev-cyber-ai-learning-lab-diagnostic.XXXXXX)" || {
    echo "Erreur : impossible de créer le dossier temporaire sécurisé." >&2
    exit 1
}
DOCKER_OUT_FILE="$TEMP_DIR/docker.out"
DOCKER_ERR_FILE="$TEMP_DIR/docker.err"
API_DIAG_ERR_FILE="$TEMP_DIR/api-diag.err"
API_BODY_FILE="$TEMP_DIR/api-health.body"
API_ERR_FILE="$TEMP_DIR/api-health.err"

cleanup() {
    rm -f -- \
        "$DOCKER_OUT_FILE" \
        "$DOCKER_ERR_FILE" \
        "$API_DIAG_ERR_FILE" \
        "$API_BODY_FILE" \
        "$API_ERR_FILE"
    rmdir -- "$TEMP_DIR" 2>/dev/null || true
}

trap cleanup EXIT

mkdir -p "$REPORT_DIR"
chmod 700 "$REPORT_DIR"

DOCKER_STATUS="KO"
DOCKER_DETAILS="Docker non testé."

API_STATUS="KO"
API_DETAILS="API non testée."
API_DIAG_STATUS="KO"
API_DIAG_DETAILS="Endpoint /diag non testé."

check_docker() {
    if ! command -v docker >/dev/null 2>&1; then
        DOCKER_STATUS="KO"
        DOCKER_DETAILS="La commande docker est introuvable."
        return
    fi

    if timeout 5 docker ps >"$DOCKER_OUT_FILE" 2>"$DOCKER_ERR_FILE"; then
        DOCKER_STATUS="OK"
        DOCKER_DETAILS="Docker répond correctement à la commande docker ps."
    else
        DOCKER_STATUS="KO"
        DOCKER_DETAILS="$(<"$DOCKER_ERR_FILE")"
    fi
}

check_api_diag() {
    if ! command -v curl >/dev/null 2>&1; then
        API_DIAG_STATUS="KO"
        API_DIAG_DETAILS="La commande curl est introuvable."
        return
    fi

    local err_file
    local http_code

    err_file="$API_DIAG_ERR_FILE"
    local curl_args=(
        -sS
        --max-time 5
        -o "$DIAG_JSON_FILE"
        -w "%{http_code}"
    )

    local diag_client_token="${DIAG_CLIENT_TOKEN:-${DIAG_ACCESS_TOKEN:-}}"
    if [ -n "$diag_client_token" ]; then
        case "$diag_client_token" in
            *[!A-Za-z0-9._~-]*)
                API_DIAG_STATUS="KO"
                API_DIAG_DETAILS="Format du jeton diagnostic invalide."
                return
                ;;
        esac
        http_code="$(
            printf 'header = "Authorization: Bearer %s"\n' "$diag_client_token" \
                | curl --config - "${curl_args[@]}" "$API_DIAG_URL" 2>"$err_file" \
                || true
        )"
    else
        http_code="$(curl "${curl_args[@]}" "$API_DIAG_URL" 2>"$err_file" || true)"
    fi

    if [ "$http_code" = "200" ]; then
        API_DIAG_STATUS="OK"
        API_DIAG_DETAILS="Réponse JSON sauvegardée dans $DIAG_JSON_FILE."
    else
        API_DIAG_STATUS="KO"
        API_DIAG_DETAILS="/diag indisponible. Code HTTP : $http_code. Erreur : $(<"$err_file")"
        rm -f "$DIAG_JSON_FILE"
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

    body_file="$API_BODY_FILE"
    err_file="$API_ERR_FILE"

    http_code="$(curl -sS --max-time 3 -o "$body_file" -w "%{http_code}" "$API_HEALTH_URL" 2>"$err_file" || true)"

    if [ "$http_code" = "200" ]; then
        API_STATUS="OK"
        API_DETAILS="L'API répond correctement avec le code HTTP 200."
    else
        API_STATUS="KO"
        API_DETAILS="L'API ne répond pas correctement. Code HTTP : $http_code. Erreur : $(<"$err_file")"
    fi
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
    echo "| API /diag | $API_DIAG_STATUS | $API_DIAG_DETAILS |" >> "$REPORT_FILE"
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

write_diag_api_check() {
    echo "" >> "$REPORT_FILE"
    echo "## Export JSON depuis /diag" >> "$REPORT_FILE"
    echo "" >> "$REPORT_FILE"
    echo "URL testée :" >> "$REPORT_FILE"
    echo "" >> "$REPORT_FILE"
    echo "    $API_DIAG_URL" >> "$REPORT_FILE"
    echo "" >> "$REPORT_FILE"
    echo "Résultat :" >> "$REPORT_FILE"
    echo "" >> "$REPORT_FILE"
    echo "$API_DIAG_DETAILS" >> "$REPORT_FILE"

    if [ -f "$DIAG_JSON_FILE" ]; then
        echo "" >> "$REPORT_FILE"
        echo "Réponse JSON sauvegardée ici :" >> "$REPORT_FILE"
        echo "" >> "$REPORT_FILE"
        echo "    $DIAG_JSON_FILE" >> "$REPORT_FILE"
    fi

    echo "" >> "$REPORT_FILE"
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
check_api_diag

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
write_diag_api_check
write_conclusion

echo "Diagnostic terminé."
echo "Docker : $DOCKER_STATUS"
echo "API : $API_STATUS"
echo "API /diag : $API_DIAG_STATUS"
echo "Rapport généré : $REPORT_FILE"
