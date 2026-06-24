.PHONY: help check check-fast check-full bootstrap bootstrap-fedora bootstrap-ubuntu build up down logs health version diag diag-json diag-md reports diagnostic diagnostic-local ansible-check check-api-contract shellcheck compose-config mtls-check mtls-generate public-config public-up public-health public-down lint-python lint run setup-dev test clean

APP_URL_FILE ?= .runtime/app_url
DEFAULT_APP_URL ?= http://127.0.0.1:8000
APP_URL ?= $(shell test -f "$(APP_URL_FILE)" && cat "$(APP_URL_FILE)" || printf '%s' "$(DEFAULT_APP_URL)")
COMPOSE ?= ./scripts/compose.sh
CURL ?= curl -fsS
MTLS_DIR ?= /etc/infra-lab/mtls
PUBLIC_COMPOSE = $(COMPOSE) -f compose.yaml -f compose.public.yaml --profile public-proxy
PUBLIC_URL ?=
PYTHON ?= python3
VENV ?= .venv
VENV_PYTHON := $(VENV)/bin/python
VALIDATION_TMP ?= /tmp/infra-dev-cyber-ai-learning-lab
ANSIBLE_LOCAL_TEMP ?= $(VALIDATION_TMP)/ansible-local
ANSIBLE_REMOTE_TMP ?= $(VALIDATION_TMP)/ansible-remote
BUILDX_CONFIG ?= $(VALIDATION_TMP)/buildx-config
VALIDATION_DOCKER_CONFIG ?= $(VALIDATION_TMP)/docker-config

define run_diag_curl
	@token="$${DIAG_CLIENT_TOKEN:-$${DIAG_ACCESS_TOKEN:-}}"; \
	if [ -n "$$token" ]; then \
		case "$$token" in *[!A-Za-z0-9._~-]*) echo "Erreur : format de jeton diagnostic invalide." >&2; exit 2;; esac; \
		printf 'header = "Authorization: Bearer %s"\n' "$$token" | $(CURL) --config - $(1); \
	else \
		$(CURL) $(1); \
	fi
endef

help:
	@echo "Commandes disponibles :"
	@echo ""
	@echo "  make help              Affiche cette aide"
	@echo "  make check             Vérification rapide du dépôt"
	@echo "  make check-fast        Alias de make check"
	@echo "  make check-full        Vérification complète avec build Docker et Ansible"
	@echo "  make bootstrap         Alias de make bootstrap-fedora"
	@echo "  make bootstrap-fedora  Prépare Fedora 44 avec BOOTSTRAP_CONFIRM=yes"
	@echo "  make bootstrap-ubuntu  Prépare Ubuntu 26.04 avec BOOTSTRAP_CONFIRM=yes"
	@echo "  make compose-config    Valide compose.yaml"
	@echo "  make mtls-check        Vérifie le jeu mTLS hors dépôt"
	@echo "  make mtls-generate     Génère le jeu mTLS après confirmation"
	@echo "  make public-config     Valide la configuration Compose publique"
	@echo "  make public-up         Vérifie mTLS puis démarre le mode public"
	@echo "  make public-health     Teste PUBLIC_URL/health en HTTPS"
	@echo "  make public-down       Arrête le mode public"
	@echo "  make check-api-contract Vérifie les routes FastAPI contre OpenAPI"
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
	@echo "  make diag-json         Génère un rapport JSON via l'API"
	@echo "  make diag-md           Génère un rapport Markdown via l'API"
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
	@echo "  MTLS_DIR=$(MTLS_DIR)"
	@echo "  PUBLIC_URL=https://<LAB_DOMAIN>"

check: check-fast

check-fast: setup-dev
	@mkdir -p "$(VALIDATION_DOCKER_CONFIG)"
	DOCKER_CONFIG="$(VALIDATION_DOCKER_CONFIG)" COMPOSE_DISABLE_ENV_FILE=1 ./scripts/check_reproducibility.sh

check-full: setup-dev
	@mkdir -p "$(VALIDATION_DOCKER_CONFIG)"
	DOCKER_CONFIG="$(VALIDATION_DOCKER_CONFIG)" COMPOSE_DISABLE_ENV_FILE=1 ./scripts/check_reproducibility.sh --full

bootstrap: bootstrap-fedora

bootstrap-fedora:
	./scripts/bootstrap_fedora44_vm.sh

bootstrap-ubuntu:
	./scripts/bootstrap_ubuntu2604_server.sh

compose-config:
	$(COMPOSE) config >/dev/null
	$(PUBLIC_COMPOSE) config >/dev/null

mtls-check:
	MTLS_DIR="$(MTLS_DIR)" ./scripts/check_mtls_files.sh

mtls-generate:
	MTLS_GENERATE_CONFIRM="$(MTLS_GENERATE_CONFIRM)" MTLS_DIR="$(MTLS_DIR)" ./scripts/generate_mtls_files.sh

public-config:
	$(PUBLIC_COMPOSE) config >/dev/null

public-up:
	MTLS_DIR="$(MTLS_DIR)" $(PUBLIC_COMPOSE) up -d --build

public-health:
	@test -n "$(PUBLIC_URL)" || { echo "Erreur : définis PUBLIC_URL=https://<LAB_DOMAIN>." >&2; exit 2; }
	@$(CURL) "$(PUBLIC_URL)/health"
	@echo ""

public-down:
	$(PUBLIC_COMPOSE) down

check-api-contract: setup-dev
	PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. $(VENV_PYTHON) scripts/check_openapi_routes.py

shellcheck:
	shellcheck scripts/*.sh backup/*.sh

lint-python: setup-dev
	PYTHONDONTWRITEBYTECODE=1 $(VENV_PYTHON) -m ruff check --no-cache app

lint: lint-python shellcheck compose-config

build:
	@mkdir -p "$(BUILDX_CONFIG)"
	BUILDX_CONFIG="$(BUILDX_CONFIG)" $(COMPOSE) build

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
	$(call run_diag_curl,"$(APP_URL)/diag")
	@echo ""

diag-json:
	$(call run_diag_curl,-X POST "$(APP_URL)/diag/export/json")
	@echo ""

diag-md:
	$(call run_diag_curl,-X POST "$(APP_URL)/diag/export/markdown")
	@echo ""

reports:
	@if [ -d outputs/reports ]; then find outputs/reports -maxdepth 1 -type f -print | sort; else echo "Aucun dossier outputs/reports pour le moment."; fi

diagnostic: diag

diagnostic-local:
	./scripts/diagnostic_local.sh

ansible-check:
	@mkdir -p "$(ANSIBLE_LOCAL_TEMP)" "$(ANSIBLE_REMOTE_TMP)"
	ANSIBLE_LOCAL_TEMP="$(ANSIBLE_LOCAL_TEMP)" ANSIBLE_REMOTE_TMP="$(ANSIBLE_REMOTE_TMP)" ansible-playbook -i ansible/inventory.yml ansible/playbooks/diagnostic.yml --check

$(VENV_PYTHON):
	$(PYTHON) -m venv $(VENV)
	$(VENV_PYTHON) -m pip install -r app/requirements-dev.txt

setup-dev: $(VENV_PYTHON)

test: setup-dev
	PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. $(VENV_PYTHON) -m pytest -p no:cacheprovider app/tests -v

clean:
	$(COMPOSE) down
