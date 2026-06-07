# infra-dev-cyber-ai-learning-lab

Lab d'apprentissage reproductible autour de Linux, réseau, Docker, FastAPI, automatisation, cybersécurité défensive et bases IA.

## Objectif

L'objectif est de fournir un dépôt simple à cloner, vérifier et lancer pour apprendre progressivement à :

1. installer les prérequis système adaptés ;
2. valider l'état du dépôt avec des commandes reproductibles ;
3. lancer une API locale avec Docker Compose ;
4. tester les endpoints `/`, `/health`, `/version` et `/diag` ;
5. générer un diagnostic local en lecture seule ;
6. arrêter proprement le lab.

Le projet reste volontairement en **mode sécurité lecture seule** : les scripts observent l'environnement local sans action destructive, sans secret et sans exposition publique directe non protégée de `/diag`.

## Cible prioritaire

La cible prioritaire de reproductibilité est **Ubuntu 24.04.4 LTS Desktop**.

Fedora 44 Workstation VM reste documentée comme environnement déjà travaillé, mais la suite de la roadmap privilégie la validation réelle sur Ubuntu 24.04.4 LTS Desktop.

## Statut du projet

Version actuelle : v0.1.0

Fonctionnalités disponibles :

- API FastAPI minimale ;
- endpoints `/`, `/health`, `/version` et `/diag` ;
- lancement avec Docker Compose ;
- commandes Makefile principales ;
- tests automatisés avec pytest ;
- lint Python avec Ruff ;
- vérification Bash avec ShellCheck ;
- validation Docker Compose ;
- validation rapide avec `make check` / `make check-fast` ;
- validation complète avec `make check-full` ;
- documentation de reproductibilité Fedora et Ubuntu ;
- rapport local read-only avec `make diagnostic-local`.

## Pré-requis

Les scripts de bootstrap installent les outils nécessaires selon la distribution :

- Git ;
- Docker Engine ;
- Docker Compose plugin (`docker compose`) ;
- Make ;
- Curl ;
- Python 3 ;
- Pytest et dépendances de développement ;
- Ansible ;
- ShellCheck.

Les dépendances Python de développement sont listées dans `app/requirements-dev.txt`.

## Reproduction locale sur Ubuntu 24.04.4 LTS Desktop

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

## Démarrage rapide pour développement local

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
| `make bootstrap-ubuntu` | Installe les prérequis sur Ubuntu 24.04.4 LTS |
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
| `make diagnostic-local` | Génère un rapport local read-only |
| `make ansible-check` | Lance le playbook Ansible en mode check |
| `make test` | Lance les tests Python |
| `make logs` | Affiche les logs Docker |
| `make down` | Arrête proprement le projet |
| `make clean` | Effectue un nettoyage léger |

## Sécurité locale

- `.env.example` expose l'API sur `127.0.0.1` par défaut.
- Ne pas remplacer la valeur locale par `0.0.0.0` sans authentification et sans reverse proxy HTTPS sécurisé.
- `/diag` retourne des informations système de diagnostic et ne doit pas être exposé publiquement sans authentification et reverse proxy sécurisé.
- Ne jamais ajouter de secrets réels dans les fichiers d'exemple `.env`.

## Tests

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
