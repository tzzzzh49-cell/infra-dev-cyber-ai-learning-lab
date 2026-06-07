# infra-dev-cyber-ai-learning-lab

Lab reproductible d'apprentissage autour de Linux, réseau, Docker, FastAPI, automatisation, cybersécurité défensive et diagnostic local en **mode lecture seule**.

## Objectif

Ce projet sert à apprendre et valider un socle infrastructure/dev/cyber/IA sans action destructive :

1. cloner le dépôt canonique ;
2. préparer les prérequis sur une distribution supportée ;
3. vérifier rapidement l'état du dépôt ;
4. lancer l'API locale avec Docker Compose ;
5. tester `/`, `/health`, `/version` et `/diag` ;
6. générer un diagnostic local read-only ;
7. arrêter proprement le lab.

## Cible prioritaire

La cible prioritaire de reproductibilité est **Ubuntu 24.04.4 LTS Desktop**.

| Distribution | Version | Statut |
|---|---|---|
| Ubuntu Desktop | 24.04.4 LTS | Cible prioritaire à valider réellement |
| Fedora Workstation VM | 44 | Base historique validée/à valider |

> Le projet **ne prétend pas** fonctionner sur toutes les distributions Linux à ce stade.

## Démarrage reproductible sur Ubuntu 24.04.4 LTS Desktop

```bash
git clone https://github.com/tzzzzh49-cell/infra-dev-cyber-ai-learning-lab.git
cd infra-dev-cyber-ai-learning-lab

make bootstrap-ubuntu
# se déconnecter / reconnecter après l'ajout au groupe docker

make check-full
make run
make health
make version
make diag
make diagnostic-local
make down
```

Documentation détaillée : `docs/reproductibilite-ubuntu-24.04.md`.

## Configuration locale sûre

Copier l'exemple si une configuration locale est nécessaire :

```bash
cp .env.example .env
```

Par défaut, l'application doit rester exposée uniquement en local :

```env
APP_HOST=127.0.0.1
APP_PORT=8000
```

Ne pas utiliser `APP_HOST=0.0.0.0` sans authentification et sans reverse proxy HTTPS sécurisé.

## Rappel sécurité

- Le projet reste en mode **lecture seule** : aucun script ne doit exécuter d'action destructive.
- Aucun secret réel ne doit être ajouté dans le dépôt ou dans les fichiers `.env*.example`.
- L'endpoint `/diag` expose des informations de diagnostic système : il ne doit **jamais** être exposé publiquement sans authentification et reverse proxy HTTPS sécurisé.
- Sur VPS, l'exposition publique devra passer par Caddy ou un reverse proxy équivalent ; ce n'est pas inclus dans les livrables de semaine 1.

## Commandes Makefile principales

| Commande | Description |
|---|---|
| `make help` | Affiche les commandes disponibles |
| `make bootstrap-ubuntu` | Installe les prérequis sur Ubuntu 24.04.4 LTS |
| `make bootstrap-fedora` | Installe les prérequis sur Fedora 44 Workstation |
| `make check` / `make check-fast` | Vérifie rapidement le dépôt |
| `make check-full` | Lance la validation complète avec build Docker et Ansible en mode check |
| `make lint` | Lance Ruff, ShellCheck et Docker Compose config |
| `make compose-config` | Valide `compose.yaml` |
| `make shellcheck` | Vérifie les scripts Bash |
| `make test` | Lance les tests Python |
| `make build` | Construit l'image Docker |
| `make up` | Démarre l'application via Docker Compose |
| `make run` | Build, démarre et attend `/health` |
| `make health` | Teste `GET /health` |
| `make version` | Teste `GET /version` |
| `make diag` | Teste `GET /diag` |
| `make diagnostic-local` | Génère un rapport local read-only dans `outputs/reports/` |
| `make ansible-check` | Lance le playbook Ansible en mode check |
| `make logs` | Affiche les logs Docker |
| `make down` | Arrête proprement le projet |
| `make clean` | Effectue un nettoyage léger limité au projet |

## Tests et validation

```bash
python3 -m pip install -r app/requirements-dev.txt
make test
make check
make check-full
```

`make check` lance les tests Python et les validations de base. `make check-full` ajoute le build Docker et le playbook Ansible en mode check.

## Documentation

- [Architecture](docs/architecture.md)
- [Sécurité](docs/securite.md)
- [Workflow Git et GitHub](docs/workflow-git.md)
- [Reproductibilité Linux générique](docs/reproductibilite-linux-generique.md)
- [Reproductibilité Fedora 44](docs/reproductibilite-fedora-44-vm.md)
- [Reproductibilité Ubuntu 24.04](docs/reproductibilite-ubuntu-24.04.md)
- [Journal d'apprentissage](docs/journal-apprentissage.md)
- [ADR-001 - Mode lecture seule](docs/decisions/ADR-001-mode-read-only.md)

La documentation évolue progressivement afin de montrer les choix techniques, les règles de sécurité et les apprentissages réalisés.
