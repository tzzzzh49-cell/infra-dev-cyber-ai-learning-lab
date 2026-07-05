#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

PUBLIC_CHECK=false
WARNING_COUNT=0

usage() {
    cat <<'USAGE'
Usage: ./scripts/migration_preflight.sh [--public]

Vérifie le dépôt avant/après migration VPS sans démarrer de service.

Sans option :
  - prérequis locaux ;
  - fichiers importants ;
  - configuration Docker Compose de base et publique ;
  - absence de secrets évidents suivis par Git.

Avec --public :
  - ajoute des contrôles metadata sur mTLS, TLS public et secrets OIDC.
  - ne lit pas ni n'affiche le contenu des secrets.
USAGE
}

case "${1:-}" in
    "")
        ;;
    --public)
        PUBLIC_CHECK=true
        ;;
    -h|--help)
        usage
        exit 0
        ;;
    *)
        echo "ERREUR : option inconnue : $1" >&2
        usage >&2
        exit 2
        ;;
esac

ok() {
    echo "OK   $1"
}

warn() {
    echo "WARN $1" >&2
    WARNING_COUNT=$((WARNING_COUNT + 1))
}

fail() {
    echo "ERREUR : $1" >&2
    exit 1
}

require_command() {
    local command_name="$1"

    if command -v "$command_name" >/dev/null 2>&1; then
        ok "$command_name -> $(command -v "$command_name")"
    else
        fail "commande manquante : $command_name"
    fi
}

optional_command() {
    local command_name="$1"

    if command -v "$command_name" >/dev/null 2>&1; then
        ok "$command_name -> $(command -v "$command_name")"
    else
        warn "commande optionnelle absente : $command_name"
    fi
}

require_path() {
    local path="$1"

    if [ -e "$path" ]; then
        ok "$path"
    else
        fail "chemin manquant : $path"
    fi
}

require_dir() {
    local path="$1"

    if [ -d "$path" ]; then
        ok "$path/"
    else
        fail "dossier manquant : $path"
    fi
}

check_commands() {
    echo "==> Commandes nécessaires"

    require_command git
    require_command python3
    require_command docker
    require_command make
    require_command curl
    optional_command restic
}

check_git() {
    local branch
    local commit
    local sensitive_tracked

    echo
    echo "==> Etat Git"

    if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
        fail "ce dossier n'est pas un dépôt Git"
    fi

    branch="$(git branch --show-current 2>/dev/null || true)"
    commit="$(git rev-parse --short HEAD 2>/dev/null || true)"
    ok "branche courante : ${branch:-detached}"
    ok "commit courant : ${commit:-inconnu}"

    if git diff --quiet -- . 2>/dev/null; then
        ok "aucune modification suivie par Git"
    else
        warn "modifications Git détectées ; migre de préférence un commit ou un tag validé"
    fi

    sensitive_tracked="$(git ls-files \
        '.env' '.env.local' '.env.vps' '.env.backup' \
        '*.pem' '*.key' '*.p12' '*.pfx' '*.token' \
        'id_rsa' 'id_ed25519' 2>/dev/null || true)"
    if [ -n "$sensitive_tracked" ]; then
        while IFS= read -r path; do
            echo "  - $path" >&2
        done <<<"$sensitive_tracked"
        fail "des fichiers sensibles semblent suivis par Git"
    fi
    ok "aucun secret évident suivi par Git"
}

check_paths() {
    echo
    echo "==> Fichiers du projet"

    local required_paths=(
        README.md
        ROADMAP.md
        Makefile
        compose.yaml
        compose.public.yaml
        app/Dockerfile
        app/main.py
        app/requirements.txt
        scripts/compose.sh
        scripts/check_reproducibility.sh
        scripts/check_mtls_files.sh
        scripts/generate_mtls_files.sh
        scripts/provision_public_proxy.sh
        backup/init-local.sh
        backup/backup-local.sh
        backup/restore-test-local.sh
        backup/restic-excludes.txt
        docs/vps/README.md
        docs/vps/09-migration-nouveau-vps.md
        docs/backups/README.md
    )

    for path in "${required_paths[@]}"; do
        require_path "$path"
    done

    require_dir outputs/reports
    require_dir outputs/logs
}

check_compose() {
    local base_config
    local public_config

    echo
    echo "==> Docker Compose"

    base_config="$(mktemp)"
    public_config="$(mktemp)"
    trap 'rm -f "$base_config" "$public_config"; trap - RETURN' RETURN

    COMPOSE_DISABLE_ENV_FILE=1 ./scripts/compose.sh config >"$base_config"
    COMPOSE_DISABLE_ENV_FILE=1 ./scripts/compose.sh -f compose.yaml -f compose.public.yaml --profile public-proxy config >"$public_config"
    ok "configuration Compose rendue sans lire .env"

    if grep -q '127.0.0.1' "$base_config"; then
        ok "FastAPI reste lié à 127.0.0.1 en configuration de base"
    else
        fail "le port FastAPI ne semble pas lié à 127.0.0.1"
    fi

    if grep -q '80:' "$public_config" && grep -q '443:' "$public_config"; then
        ok "le profil public prépare HTTP/HTTPS via Nginx"
    else
        warn "le profil public ne montre pas clairement les ports 80 et 443"
    fi
}

check_outputs_metadata() {
    local report_count
    local log_count

    echo
    echo "==> Données générées"

    report_count="$(find outputs/reports -maxdepth 1 -type f 2>/dev/null | wc -l)"
    log_count="$(find outputs/logs -maxdepth 1 -type f 2>/dev/null | wc -l)"
    ok "rapports à revoir avant migration : $report_count fichier(s)"
    ok "logs locaux à traiter selon besoin : $log_count fichier(s)"
}

check_file_metadata_var() {
    local var_name="$1"
    local expected="$2"
    local path="${!var_name:-}"
    local mode

    if [ -z "$path" ]; then
        warn "$var_name non défini dans l'environnement courant"
        return
    fi

    if [ ! -f "$path" ]; then
        fail "$var_name pointe vers un fichier absent"
    fi

    if [ ! -s "$path" ]; then
        fail "$var_name pointe vers un fichier vide"
    fi

    mode="$(stat -c '%a' "$path")"
    case "$expected:$mode" in
        private:400|private:440|private:600|private:640|public:444|public:644|public:640)
            ok "$var_name présent avec permissions $mode"
            ;;
        *)
            warn "$var_name présent, permissions à relire : $mode"
            ;;
    esac
}

check_var_defined() {
    local var_name="$1"

    if [ -n "${!var_name:-}" ]; then
        ok "$var_name défini"
    else
        warn "$var_name non défini dans l'environnement courant"
    fi
}

check_public_runtime() {
    echo
    echo "==> Runtime public (metadata seulement)"

    check_var_defined LAB_DOMAIN
    check_var_defined OIDC_ISSUER_URL
    check_var_defined OIDC_JWKS_URL
    check_var_defined OIDC_CLIENT_ID
    check_var_defined OIDC_AUDIENCE

    MTLS_DIR="${MTLS_DIR:-/etc/infra-lab/mtls}" ./scripts/check_mtls_files.sh
    check_file_metadata_var PUBLIC_TLS_CERT_FILE public
    check_file_metadata_var PUBLIC_TLS_KEY_FILE private
    check_file_metadata_var OIDC_CLIENT_SECRET_FILE private
    check_file_metadata_var OIDC_COOKIE_SECRET_FILE private
}

check_commands
check_git
check_paths
check_compose
check_outputs_metadata

if [ "$PUBLIC_CHECK" = true ]; then
    check_public_runtime
fi

echo
if [ "$WARNING_COUNT" -eq 0 ]; then
    echo "Migration preflight OK."
else
    echo "Migration preflight terminé avec $WARNING_COUNT avertissement(s)."
fi
