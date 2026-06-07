# Network and Systems Training

Projet d'apprentissage autour de Linux, réseau, Docker, FastAPI, automatisation et diagnostic défensif.

## Objectif

Permettre à une personne de :

1. cloner le dépôt ;
2. installer les prérequis adaptés à sa distribution ;
3. valider rapidement l'état du dépôt ;
4. lancer l'application avec Docker Compose ;
5. tester `/`, `/health`, `/version`, `/diag` ;
6. arrêter proprement le projet.

## Statut du projet

Version actuelle : v0.1.0

Le projet est actuellement une base de lab systèmes/réseaux/DevOps/cybersécurité.

Fonctionnalités disponibles :
- API FastAPI minimale ;
- endpoints `/`, `/health`, `/version` et `/diag` ;
- lancement avec Docker Compose ;
- commandes Makefile principales ;
- tests automatisés avec pytest ;
- lint Python avec Ruff ;
- vérification Bash avec ShellCheck ;
- validation Docker Compose ;
- validation rapide du dépôt avec `make check` / `make check-fast` ;
- validation complète de reproductibilité avec `make check-full` ;
- reproduction testée sur VM Fedora 44 ;
- documentation de reproductibilité Fedora et Ubuntu ;
- documentation technique initiale ;
- règles de sécurité en lecture seule.

Fonctionnalités prévues :
- CI GitHub Actions ;
- diagnostic réseau plus avancé ;
- déploiement VPS ;
- intégration progressive OpenAI API ;
- intégration contrôlée OpenClaw.

## Matrice de compatibilité Linux

| Distribution | Version | Statut |
|---|---|---|
| Fedora Workstation VM | 44 | Cible validée/à valider |
| Ubuntu LTS | 24.04.4 | Cible validée/à valider |

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

Les prérequis sont installés automatiquement via les scripts de bootstrap ci-dessous.

Les dépendances Python de développement sont listées dans `app/requirements-dev.txt`.

## Bootstrap par distribution

### Fedora 44 Workstation VM

```bash
make bootstrap-fedora
```

Documentation détaillée : `docs/reproductibilite-fedora-44-vm.md`.

### Ubuntu 24.04.4 LTS

```bash
make bootstrap-ubuntu
```

Documentation détaillée : `docs/reproductibilite-ubuntu-24.04.md`.

## Démarrage rapide

```bash
git clone https://github.com/tzzzzh49-cell/network-and-systems-training.git
cd network-and-systems-training
make check
make build
make up
curl -fsS http://127.0.0.1:8000/
make health
make version
make diag
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

## Commandes Makefile

| Commande | Description |
|---|---|
| `make help` | Affiche les commandes disponibles |
| `make check` | Vérifie rapidement le dépôt |
| `make check-fast` | Alias de `make check` |
| `make check-full` | Lance la validation complète avec build Docker et Ansible |
| `make bootstrap` | Alias de `make bootstrap-fedora` |
| `make bootstrap-fedora` | Installe les prérequis sur Fedora 44 VM |
| `make bootstrap-ubuntu` | Installe les prérequis sur Ubuntu 24.04.4 LTS |
| `make compose-config` | Valide `compose.yaml` |
| `make shellcheck` | Vérifie les scripts Bash |
| `make build` | Construit l'image Docker |
| `make up` | Démarre l'application via Docker Compose |
| `make run` | Build, démarre et attend `/health` |
| `make health` | Teste `GET /health` |
| `make version` | Teste `GET /version` |
| `make diag` | Teste `GET /diag` |
| `make diagnostic-local` | Génère un rapport local read-only |
| `make ansible-check` | Lance le playbook Ansible en mode check |
| `make test` | Lance les tests Python |
| `make logs` | Affiche les logs Docker |
| `make down` | Arrête proprement le projet |
| `make clean` | Effectue un nettoyage léger |

## Tests

Les tests automatisés couvrent les fonctions associées aux endpoints FastAPI.

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

- [Architecture](docs/architecture.md)
- [Sécurité](docs/securite.md)
- [Workflow Git et GitHub](docs/workflow-git.md)
- [Reproductibilité Linux générique](docs/reproductibilite-linux-generique.md)
- [Reproductibilité Fedora 44](docs/reproductibilite-fedora-44-vm.md)
- [Reproductibilité Ubuntu 24.04](docs/reproductibilite-ubuntu-24.04.md)
- [Journal d'apprentissage](docs/journal-apprentissage.md)
- [ADR-001 - Mode lecture seule](docs/decisions/ADR-001-mode-read-only.md)

Le projet est documenté progressivement afin de montrer les choix techniques, les règles de sécurité et les apprentissages réalisés.
