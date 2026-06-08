.PHONY: help check check-fast check-full bootstrap bootstrap-fedora bootstrap-ubuntu build up down logs health version diag diag-json diag-md reports diagnostic diagnostic-local ansible-check shellcheck compose-config lint-python lint run setup-dev test clean

APP_URL_FILE ?= .runtime/app_url
DEFAULT_APP_URL ?= http://127.0.0.1:8000
APP_URL ?= $(shell test -f "$(APP_URL_FILE)" && cat "$(APP_URL_FILE)" || printf '%s' "$(DEFAULT_APP_URL)")
COMPOSE ?= ./scripts/compose.sh
CURL ?= curl -fsS
PYTHON ?= python3
VENV ?= .venv
VENV_PYTHON := $(VENV)/bin/python

help:
	@echo "Commandes disponibles :"
	@echo ""
	@echo "  make help              Affiche cette aide"
	@echo "  make check             Vérification rapide du dépôt"
	@echo "  make check-fast        Alias de make check"
	@echo "  make check-full        Vérification complète avec build Docker et Ansible"
	@echo "  make bootstrap         Alias de make bootstrap-fedora"
	@echo "  make bootstrap-fedora  Prépare l'environnement Fedora 44"
	@echo "  make bootstrap-ubuntu  Prépare l'environnement Ubuntu 24.04.4 LTS"
	@echo "  make compose-config    Valide compose.yaml"
	@echo "  make shellcheck        Vérifie les scripts Bash"
	@echo "  make lint-python       Vérifie le code Python avec ruff"
	@echo "  make lint              Lance ruff, ShellCheck et Docker Compose config"
	@echo "  make build             Construit l'image Docker"
	@echo "  make up                Lance l'application"
	@echo "  make run               Build, démarre et attend /health"
	@echo "  make down              Arrête l'application"
	@echo "  make logs              Affiche les logs Docker"
	@echo "  make health            Teste l'endpoint /health"
	@echo "  make version           Teste l'endpoint /version"
	@echo "  make diag              Teste l'endpoint /diag"
	@echo "  make diag-json         Génère un rapport JSON via /diag/export/json"
	@echo "  make diag-md           Génère un rapport Markdown via /diag/export/markdown"
	@echo "  make reports           Liste les rapports locaux"
	@echo "  make diagnostic        Alias de make diag"
	@echo "  make diagnostic-local  Génère un rapport local read-only"
	@echo "  make ansible-check     Lance le playbook Ansible en mode check"
	@echo "  make setup-dev         Prépare l'environnement Python de développement"
	@echo "  make test              Lance les tests Python"
	@echo "  make clean             Nettoyage léger"
	@echo ""
	@echo "Variable utile :"
	@echo "  APP_URL=$(APP_URL)"

check: check-fast

check-fast: setup-dev
	./scripts/check_reproducibility.sh

check-full: setup-dev
	./scripts/check_reproducibility.sh --full

bootstrap: bootstrap-fedora

bootstrap-fedora:
	./scripts/bootstrap_fedora44_vm.sh

bootstrap-ubuntu:
	./scripts/bootstrap_ubuntu2404.sh

compose-config:
	$(COMPOSE) config >/dev/null

shellcheck:
	shellcheck scripts/*.sh

lint-python: setup-dev
	$(VENV_PYTHON) -m ruff check app

lint: lint-python shellcheck compose-config

build:
	$(COMPOSE) build

up:
	$(COMPOSE) up -d

run:
	./scripts/run_lab.sh

down:
	$(COMPOSE) down
	@rm -f $(APP_URL_FILE)

logs:
	$(COMPOSE) logs -f

health:
	@$(CURL) $(APP_URL)/health
	@echo ""

version:
	@$(CURL) $(APP_URL)/version
	@echo ""

diag:
	@$(CURL) $(APP_URL)/diag
	@echo ""

diag-json:
	@$(CURL) -X POST $(APP_URL)/diag/export/json
	@echo ""

diag-md:
	@$(CURL) -X POST $(APP_URL)/diag/export/markdown
	@echo ""

reports:
	@if [ -d outputs/reports ]; then find outputs/reports -maxdepth 1 -type f -print | sort; else echo "Aucun dossier outputs/reports."; fi

diagnostic: diag

diagnostic-local:
	./scripts/diagnostic_local.sh

ansible-check:
	ansible-playbook -i ansible/inventory.yml ansible/playbooks/diagnostic.yml --check

$(VENV_PYTHON):
	$(PYTHON) -m venv $(VENV)
	$(VENV_PYTHON) -m pip install --upgrade pip
	$(VENV_PYTHON) -m pip install -r app/requirements-dev.txt

setup-dev: $(VENV_PYTHON)

test: setup-dev
	PYTHONPATH=. $(VENV_PYTHON) -m pytest app/tests -v

clean:
	$(COMPOSE) down
