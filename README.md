# Infra Dev Cyber AI Learning Lab


[![CI](https://github.com/tzzzzh49-cell/infra-dev-cyber-ai-learning-lab/actions/workflows/ci.yml/badge.svg?branch=master)](https://github.com/tzzzzh49-cell/infra-dev-cyber-ai-learning-lab/actions/workflows/ci.yml)

Projet d'apprentissage reproductible autour de Linux, réseau, Docker, FastAPI, automatisation, diagnostic défensif et bonnes pratiques DevSecOps.

## Objectif

`infra-dev-cyber-ai-learning-lab` sert de lab local pour apprendre à :

1. cloner un dépôt et installer les prérequis d'une distribution cible ;
2. valider rapidement l'état du dépôt ;
3. lancer une API FastAPI avec Docker Compose ;
4. tester les endpoints `/`, `/health`, `/version` et `/diag` ;
5. générer un diagnostic local en lecture seule ;
6. arrêter proprement le projet.

Le projet doit rester **reproductible en priorité sur Ubuntu 26.04 LTS Server** et conserver un mode sécurité **lecture seule** : aucune commande destructive, aucun secret et aucune exposition publique non protégée de `/diag`.

## Statut du projet

Version actuelle : v0.3.2 (durcissement Docker, timeout configurable, jetons hashés et documentation). Schéma de diagnostic : v0.3.0.

Fonctionnalités disponibles :

- API FastAPI minimale ;
- endpoints `/`, `/health`, `/version`, `/diag`, `/diag/export/json` et `/diag/export/markdown` ;
- lancement avec Docker Compose ;
- commandes Makefile principales ;
- tests automatisés avec pytest ;
- lint Python avec Ruff ;
- vérification Bash avec ShellCheck ;
- validation Docker Compose ;
- validation rapide du dépôt avec `make check` / `make check-fast` ;
- validation complète de reproductibilité avec `make check-full` ;
- CI GitHub Actions minimale sur `push` et `pull_request` vers `master` ;
- `AGENTS.md` documenté pour les agents IA ;
- tests FastAPI renforcés avec `TestClient` ;
- diagnostic réseau avancé en lecture seule ;
- export JSON du diagnostic ;
- export Markdown du diagnostic ;
- rapports locaux dans `outputs/reports` ;
- documentation de reproductibilité Fedora et Ubuntu ;
- documentation préparatoire VPS, backups et Ubuntu Server pour v0.4.0 ;
- base Restic local-first pour backups et drill de restauration local ;
- préparation Restic distante S3-compatible avec placeholders uniquement ;
- image Docker multi-étapes avec runtime non-root ;
- timeout de diagnostic configurable via `DIAG_COMMAND_TIMEOUT` ;
- protection `/diag` par token clair privé ou hash `DIAG_ACCESS_TOKEN_SHA256` ;
- génération locale de jeton avec `scripts/generate_diag_token.py` ;
- profil Compose préparatoire `future-persistence` pour Postgres, inactif par défaut ;
- placeholders OpenAI API read-only sans appel réel obligatoire ;
- runbooks OpenClaw documentaires non actifs ;
- règles de sécurité en lecture seule.

Fonctionnalités prévues plus tard :

- déploiement VPS réel ;
- intégration progressive OpenAI API ;
- intégration contrôlée OpenClaw.

## Cible prioritaire

| Distribution | Version | Statut |
|---|---|---|
| Ubuntu Server LTS | 26.04 | Cible prioritaire, procédure et checklist Server préparées |
| Fedora Workstation VM | 44 | Cible secondaire, validation séparée à maintenir |
| Ubuntu Desktop LTS | 24.04.4 | Historique, reproductibilité validée à 100 % |

> Le projet **ne prétend pas** fonctionner sur toutes les distributions Linux à ce stade.

## Pré-requis

- Git
- Docker Engine
- Docker Compose plugin (`docker compose`)
- Make
- Curl
- Python 3
- Pytest
- Ansible
- ShellCheck

Les prérequis sont installés automatiquement via les scripts de bootstrap ci-dessous. Les dépendances Python de développement sont listées dans `app/requirements-dev.txt`.

## Reproduction locale Ubuntu 26.04 LTS Server

```bash
git clone https://github.com/tzzzzh49-cell/infra-dev-cyber-ai-learning-lab.git
cd infra-dev-cyber-ai-learning-lab

make bootstrap-ubuntu
# se déconnecter / reconnecter après l'ajout au groupe docker

make check
make check-full
make run
make health
make version
make diag
make diag-json
make diag-md
make diagnostic-local
make reports
backup/init-local.sh
backup/backup-local.sh
backup/restore-test-local.sh
make down
```

Documentation détaillée : `docs/reproductibilite-ubuntu-26.04-server.md`. Journal de validation : `docs/validations/ubuntu-26.04-server-vm.md`.

La documentation Ubuntu Server décrit la procédure attendue et la checklist de validation. Elle ne doit être marquée comme réellement validée que lorsque les commandes ont été rejouées sur une VM Ubuntu 26.04 LTS Server propre et que les résultats sont consignés dans le journal de validation.

## Bootstrap par distribution

### Fedora 44 Workstation VM

```bash
make bootstrap-fedora
```

Documentation détaillée : `docs/reproductibilite-fedora-44-vm.md`.

### Ubuntu 26.04 LTS Server

```bash
make bootstrap-ubuntu
```

Documentation détaillée : `docs/reproductibilite-ubuntu-26.04-server.md`.

## Démarrage rapide local

```bash
git clone https://github.com/tzzzzh49-cell/infra-dev-cyber-ai-learning-lab.git
cd infra-dev-cyber-ai-learning-lab
make check
make build
make up
curl -fsS http://127.0.0.1:8000/
make health
make version
make diag
make diag-json
make diag-md
make reports
make down
```

Pour construire, démarrer et attendre automatiquement que `/health` réponde :

```bash
make run
```

Pour lancer la validation lourde avant une Pull Request :

```bash
make check-full
```

## Commandes Makefile principales

| Commande | Description |
|---|---|
| `make help` | Affiche les commandes disponibles |
| `make check` | Vérifie rapidement le dépôt |
| `make check-fast` | Alias de `make check` |
| `make check-full` | Lance la validation complète avec build Docker et Ansible |
| `make bootstrap` | Alias de `make bootstrap-fedora` |
| `make bootstrap-fedora` | Installe les prérequis sur Fedora 44 VM |
| `make bootstrap-ubuntu` | Installe les prérequis sur Ubuntu 26.04 LTS Server |
| `make compose-config` | Valide `compose.yaml` |
| `make shellcheck` | Vérifie les scripts Bash |
| `make lint-python` | Vérifie le code Python avec Ruff |
| `make lint` | Lance Ruff, ShellCheck et Docker Compose config |
| `make build` | Construit l'image Docker |
| `make up` | Démarre l'application via Docker Compose |
| `make run` | Build, démarre et attend `/health` |
| `make health` | Teste `GET /health` |
| `make version` | Teste `GET /version` |
| `make diag` | Teste `GET /diag` |
| `make diag-json` | Génère un rapport JSON via `POST /diag/export/json` |
| `make diag-md` | Génère un rapport Markdown via `POST /diag/export/markdown` |
| `make reports` | Liste les rapports dans `outputs/reports` sans échouer si le dossier est absent |
| `make diagnostic-local` | Génère un rapport local read-only |
| `make ansible-check` | Lance le playbook Ansible en mode check |
| `make test` | Lance les tests Python |
| `make logs` | Affiche les logs Docker |
| `make down` | Arrête proprement le projet |
| `make clean` | Effectue un nettoyage léger |

## Sécurité locale

La configuration locale doit rester sûre par défaut :

- `.env.example` utilise `APP_HOST=127.0.0.1` pour exposer l'API uniquement sur la machine locale ;
- ne pas utiliser `APP_HOST=0.0.0.0` sans authentification et sans reverse proxy HTTPS sécurisé ;
- `/diag` peut contenir des informations système et **ne doit pas être exposé publiquement** sans authentification et reverse proxy sécurisé ;
- en mode `APP_ENV=vps`, `/diag`, `/diag/export/json` et `/diag/export/markdown` exigent un token clair privé ou `DIAG_ACCESS_TOKEN_SHA256` ;
- si `APP_ENV=vps` est actif mais qu'aucun token ni hash n'est configuré, les routes de diagnostic refusent l'accès au lieu de s'exposer sans protection ;
- `DIAG_COMMAND_TIMEOUT` vaut `3` secondes par défaut et peut être ajusté raisonnablement selon l'environnement ;
- aucun secret réel ne doit être ajouté dans les fichiers `.env*.example`, la documentation ou les scripts.

Exemples d'appels protégés : [docs/api-examples.md](docs/api-examples.md).

## Tests

Les tests automatisés couvrent les endpoints FastAPI avec `TestClient` et les fonctions de diagnostic isolées lorsque des fichiers sont écrits.

```bash
python3 -m pip install -r app/requirements-dev.txt
make test
```

`make check` lance aussi ces tests, en plus des vérifications de fichiers, syntaxe Python, Docker Compose et ShellCheck.

## Workflow de développement recommandé

```bash
git switch master
git pull
git switch -c nom-de-branche
make check
# modifications
make check
git status
git diff
git add .
git commit -m "Message clair"
git push origin nom-de-branche
```

Ensuite, ouvrir une Pull Request sur GitHub pour relire et intégrer la branche.

## Documentation

- [Sommaire documentation](docs/README.md)
- [Architecture](docs/architecture.md)
- [Architecture EN](docs/architecture.en.md)
- [Sécurité](docs/securite.md)
- [Security EN](docs/security.en.md)
- [Workflow Git et GitHub](docs/workflow-git.md)
- [Reproductibilité Linux générique](docs/reproductibilite-linux-generique.md)
- [Reproductibilité Fedora 44](docs/reproductibilite-fedora-44-vm.md)
- [Validation Ubuntu 26.04 Server](docs/validations/ubuntu-26.04-server-vm.md)
- [Préparation VPS v0.4.0](docs/vps/README.md)
- [Backups](docs/backups/README.md)
- [OpenAI API read-only](docs/ai/README.md)
- [Modèle OpenClaw contrôlé](openclaw/security-model.md)
- [Reproductibilité Ubuntu 26.04 Server](docs/reproductibilite-ubuntu-26.04-server.md)
- [Ubuntu 26.04 Server EN](docs/reproducibility-ubuntu-26.04-server.en.md)
- [Diagnostic réseau avancé v0.3.0](docs/diagnostic-reseau-v0.3.md)
- [Exemples d'appels API protégés](docs/api-examples.md)
- [Journal d'apprentissage](docs/journal-apprentissage.md)
- [ADR-001 - Mode lecture seule](docs/decisions/ADR-001-mode-read-only.md)

Le projet est documenté progressivement afin de montrer les choix techniques, les règles de sécurité et les apprentissages réalisés.
