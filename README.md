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

Version actuelle : v0.3.2 (durcissement Docker, diagnostics protégés, timeouts configurables et documentation). Schéma de diagnostic : v0.3.0.

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
- CI renforcée avec Bandit, Gitleaks et Trivy bloquant sur les CVE élevées et critiques ;
- Dependabot pour suivre les mises à jour Python, GitHub Actions et Docker ;
- `AGENTS.md` documenté pour les agents IA ;
- tests FastAPI centrés sur les routes, dépendances de sécurité et fonctions de diagnostic ;
- diagnostic réseau avancé en lecture seule ;
- protection locale par hash et protection VPS OAuth2/OIDC avec RBAC ;
- export JSON du diagnostic ;
- export Markdown du diagnostic ;
- diagnostics sérialisés et rétention des 20 derniers exports par format ;
- rapports locaux dans `outputs/reports` ;
- logs applicatifs dans `outputs/logs/app.log`, hors dépôt ;
- documentation de reproductibilité Fedora et Ubuntu ;
- documentation préparatoire VPS, backups et Ubuntu Server pour v0.4.0 ;
- base Restic local-first pour backups et drill de restauration local ;
- préparation Restic distante S3-compatible avec placeholders uniquement ;
- image Docker multi-étapes avec runtime non-root ;
- timeout et tentatives de diagnostic configurables via `DIAG_COMMAND_TIMEOUT` et `DIAG_COMMAND_RETRIES` ;
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
| Conteneur Python slim | 3.12 | Cible Compose principale pour l'API |
| Autres distributions Linux | variable | Support non officiel : les commandes absentes doivent être signalées sans casser le diagnostic |

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

Les prérequis sont installés via les scripts de bootstrap ci-dessous, après validation humaine explicite. Ces scripts utilisent `sudo`, installent Docker et peuvent retirer d'anciens paquets Docker conflictuels. Les dépendances Python de développement sont listées dans `app/requirements-dev.txt`.

## Reproduction locale Ubuntu 26.04 LTS Server

```bash
git clone https://github.com/tzzzzh49-cell/infra-dev-cyber-ai-learning-lab.git
cd infra-dev-cyber-ai-learning-lab

BOOTSTRAP_CONFIRM=yes make bootstrap-ubuntu
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
BOOTSTRAP_CONFIRM=yes make bootstrap-fedora
```

Documentation détaillée : `docs/reproductibilite-fedora-44-vm.md`.

### Ubuntu 26.04 LTS Server

```bash
BOOTSTRAP_CONFIRM=yes make bootstrap-ubuntu
```

Documentation détaillée : `docs/reproductibilite-ubuntu-26.04-server.md`.

## Démarrage rapide local

```bash
git clone https://github.com/tzzzzh49-cell/infra-dev-cyber-ai-learning-lab.git
cd infra-dev-cyber-ai-learning-lab
make check
python3 scripts/generate_diag_token.py
export APP_ENV=lab
export DIAG_ACCESS_TOKEN='<JETON_AFFICHE_PAR_LE_SCRIPT>'
export DIAG_ACCESS_TOKEN_HASH='<HASH_AFFICHE_PAR_LE_SCRIPT>'
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

Pour un essai de développement strictement local sans jeton, définir explicitement
`APP_ENV=local` et `DIAG_PROTECTION_DISABLED=true`. Cette désactivation est ignorée
hors environnements locaux.

## Commandes Makefile principales

| Commande | Description |
|---|---|
| `make help` | Affiche les commandes disponibles |
| `make check` | Vérifie rapidement le dépôt |
| `make check-fast` | Alias de `make check` |
| `make check-full` | Lance la validation complète avec build Docker et Ansible |
| `make bootstrap` | Alias de `make bootstrap-fedora` |
| `make bootstrap-fedora` | Installe les prérequis sur Fedora 44 VM après `BOOTSTRAP_CONFIRM=yes` |
| `make bootstrap-ubuntu` | Installe les prérequis sur Ubuntu 26.04 LTS Server après `BOOTSTRAP_CONFIRM=yes` |
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

- Compose lie toujours le port API à `127.0.0.1` ;
- `/diag` exige un JWT OIDC signé en VPS ; l'issuer, l'audience, la signature,
  l'expiration, la durée, la taille de clé, le rôle et la MFA admin sont validés
  dans l'API ;
- `DIAG_ACCESS_TOKEN_HASH` et `DIAG_ACCESS_TOKEN` sont réservés au lab local ;
- OAuth2 Proxy gère Authorization Code avec PKCE S256, sans mot de passe local ;
- `DIAG_PROTECTION_DISABLED=true` est réservé au développement local explicite (`APP_ENV=local`, `dev`, `development` ou `test`) ;
- `DIAG_COMMAND_TIMEOUT` vaut `3` secondes par défaut et peut être ajusté raisonnablement selon l'environnement ;
- aucun secret réel ne doit être ajouté dans les fichiers `.env*.example`, la documentation ou les scripts.

Générer un jeton pour le lab local uniquement :

```bash
python3 scripts/generate_diag_token.py
```

Stocker seulement le hash côté application locale. En VPS, suivre
[`docs/vps/08-authentification-oidc.md`](docs/vps/08-authentification-oidc.md).

Exemples d'appels protégés : [docs/api-examples.md](docs/api-examples.md).

## Journaux

L'application utilise la bibliothèque Python `logging` avec sortie console et fichier rotatif. Par défaut, le fichier est `outputs/logs/app.log`, ignoré par Git. La variable `APP_LOG_FILE` permet d'utiliser un autre chemin ou un collecteur monté dans le conteneur.

## Dépendances et CVE

Dependabot ouvre des Pull Requests pour les dépendances Python, GitHub Actions et Docker. Les mainteneurs doivent surveiller les CVE, relire les changelogs des dépendances critiques et lancer au minimum `make check`, `make test`, `make lint` et `make compose-config` avant merge.

## Tests

Les tests automatisés couvrent les routes FastAPI, la dépendance d'authentification diagnostic et les fonctions de diagnostic isolées lorsque des fichiers sont écrits.

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

- [English README](README.en.md)
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
