#!/usr/bin/env bash
set -euo pipefail

MODE="quick"

usage() {
    cat <<'USAGE'
Usage: ./scripts/check_reproducibility.sh [--quick|--full]

--quick  Vérifie les prérequis, les fichiers, la syntaxe Python, les tests, Compose et Bash.
--full   Exécute aussi le build Docker et le playbook Ansible en mode check.
USAGE
}

case "${1:-}" in
    ""|--quick)
        MODE="quick"
        ;;
    --full)
        MODE="full"
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

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

PYTHON_CMD="${PYTHON:-python3}"
if [ -x ".venv/bin/python" ]; then
    PYTHON_CMD=".venv/bin/python"
fi

require_command() {
    local cmd="$1"

    if command -v "$cmd" >/dev/null 2>&1; then
        echo "OK   $cmd -> $(command -v "$cmd")"
    else
        echo "ERREUR : commande manquante : $cmd" >&2
        exit 1
    fi
}

require_path() {
    local path="$1"

    if [ -e "$path" ]; then
        echo "OK   $path"
    else
        echo "ERREUR : fichier manquant : $path" >&2
        exit 1
    fi
}

check_no_conflict_markers() {
    echo
    echo "==> Recherche de marqueurs de conflit Git"

    if grep -R --line-number --exclude-dir=.git --exclude-dir=.venv --exclude-dir=outputs --exclude='*.pyc' -E '^(<<<<<<<|=======|>>>>>>>)' .; then
        echo "ERREUR : des marqueurs de conflit Git restent dans le dépôt." >&2
        exit 1
    fi

    echo "OK   aucun marqueur de conflit détecté"
}

check_commands() {
    echo "==> Vérification des commandes"

    local commands=(
        git
        python3
        docker
        make
        curl
        shellcheck
        ansible-playbook
    )

    for cmd in "${commands[@]}"; do
        require_command "$cmd"
    done
}

check_versions() {
    echo
    echo "==> Versions"
    git --version
    "$PYTHON_CMD" --version
    docker --version
    ./scripts/compose.sh version
    ansible-playbook --version | head -n 1
    shellcheck --version | head -n 2
}

check_paths() {
    echo
    echo "==> Vérification des fichiers importants"

    local required_paths=(
        README.md
        ROADMAP.md
        AGENTS.md
        compose.yaml
        app/Dockerfile
        app/main.py
        app/requirements.txt
        ansible/inventory.yml
        ansible/playbooks/diagnostic.yml
        scripts/bootstrap_fedora44_vm.sh
        scripts/bootstrap_ubuntu2404.sh
        scripts/compose.sh
        scripts/diagnostic_local.sh
        scripts/run_lab.sh
        .env.example
    )

    for path in "${required_paths[@]}"; do
        require_path "$path"
    done
}

check_python() {
    echo
    echo "==> Vérification Python"
    "$PYTHON_CMD" -m py_compile app/main.py
    echo "OK   app/main.py est syntaxiquement valide"
}

check_ruff() {
    echo
    echo "==> Vérification Ruff"

    if ! "$PYTHON_CMD" -m ruff --version >/dev/null 2>&1; then
        echo "ERREUR : ruff est introuvable." >&2
        echo "Installe les dépendances de développement :" >&2
        echo "  make setup-dev" >&2
        exit 1
    fi

    "$PYTHON_CMD" -m ruff check app
    echo "OK   Ruff validé"
}

check_pytest() {
    echo
    echo "==> Tests Python"

    if [ ! -d app/tests ]; then
        echo "ERREUR : dossier de tests introuvable : app/tests" >&2
        echo "Crée d'abord les tests pytest dans app/tests/." >&2
        exit 1
    fi

    if ! "$PYTHON_CMD" -m pytest --version >/dev/null 2>&1; then
        echo "ERREUR : pytest est introuvable." >&2
        echo "Installe les dépendances de développement :" >&2
        echo "  make setup-dev" >&2
        exit 1
    fi

    PYTHONPATH=. "$PYTHON_CMD" -m pytest app/tests -v
    echo "OK   tests Python validés"
}

check_compose() {
    echo
    echo "==> Vérification Docker Compose"
    ./scripts/compose.sh config >/dev/null
    echo "OK   compose.yaml est valide"
}

check_shell_scripts() {
    echo
    echo "==> Vérification ShellCheck"
    shellcheck scripts/*.sh
    echo "OK   scripts Bash validés"
}

run_full_checks() {
    echo
    echo "==> Build Docker"
    ./scripts/compose.sh build

    echo
    echo "==> Test Ansible en mode check"
    ansible-playbook -i ansible/inventory.yml ansible/playbooks/diagnostic.yml --check
}

check_commands
check_versions
check_paths
check_no_conflict_markers
check_python
check_ruff
check_pytest
check_compose
check_shell_scripts

if [ "$MODE" = "full" ]; then
    run_full_checks
fi

echo
echo "Reproductibilité $MODE OK."
