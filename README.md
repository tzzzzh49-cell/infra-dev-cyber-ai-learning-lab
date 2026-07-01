# Profil

Administrateur systèmes/réseaux junior en construction, orienté Linux, Docker, sécurité défensive, automatisation et documentation d'exploitation.

## Projet principal

Je construis [`infra-dev-cyber-ai-learning-lab`](https://github.com/tzzzzh49-cell/infra-dev-cyber-ai-learning-lab), un lab d'infrastructure sécurisé, reproductible et documenté.

Le projet n'est pas présenté comme un simple projet IA : il sert surtout à démontrer une démarche d'exploitation d'infrastructure, avec des diagnostics système/réseau en lecture seule et des procédures rejouables.

Déjà visible dans le dépôt :

- API FastAPI avec endpoints de santé, version, diagnostic et exports ;
- Docker Compose pour lancer le lab localement ;
- diagnostics système/réseau en lecture seule ;
- tests Python, Ruff, ShellCheck et validation Docker Compose ;
- CI GitHub Actions avec contrôles qualité et sécurité ;
- image Docker durcie avec utilisateur non-root ;
- documentation sécurité, architecture, VPS et sauvegardes ;
- scripts Restic local-first et restauration de test locale.

En cours ou préparé :

- validation Ubuntu Server ;
- préparation VPS documentée ;
- DNS, HTTPS et reverse proxy documentés ;
- protection de `/diag` avant toute exposition publique ;
- Restic distant S3-compatible avec placeholders uniquement ;
- IA utilisée comme aide à l'analyse, sans exécution automatique de commandes dangereuses.

Documentation technique : [`docs/README.md`](docs/README.md).

## Compétences mises en pratique

- **Systèmes** : Linux, SSH, utilisateurs, services, logs.
- **Réseau** : DNS, HTTPS, reverse proxy, diagnostic réseau.
- **Conteneurs** : Docker, Docker Compose, images non-root.
- **Sécurité** : moindre privilège, secrets hors Git, lecture seule, CI sécurité.
- **Automatisation** : Makefile, scripts Bash, Ansible local, GitHub Actions.
- **Documentation** : runbooks, checklists, journaux de validation.

## Ce que je construis actuellement

Je transforme progressivement un lab local reproductible en portfolio d'exploitation d'infrastructure.

Priorités actuelles :

- rejouer et documenter la validation Ubuntu Server ;
- consolider la préparation VPS ;
- tester les sauvegardes et restaurations ;
- maintenir la documentation sécurité ;
- préparer une exposition publique limitée, protégée et vérifiable.

## Preuves concrètes dans mes dépôts

- [`app/`](app/) : API FastAPI, authentification et diagnostics.
- [`compose.yaml`](compose.yaml) et [`app/Dockerfile`](app/Dockerfile) : exécution conteneurisée et durcissement Docker.
- [`Makefile`](Makefile) : commandes de validation, tests, lint, diagnostics et sauvegardes.
- [`.github/workflows/ci.yml`](.github/workflows/ci.yml) : CI GitHub Actions.
- [`backup/`](backup/) : scripts Restic locaux et restauration de test.
- [`docs/vps/`](docs/vps/) : préparation VPS, SSH, firewall, Docker, Compose, HTTPS, DNS et OIDC.
- [`docs/securite.md`](docs/securite.md) : posture de sécurité du lab.

## Objectifs à court terme

- finaliser une validation propre sur Ubuntu Server ;
- documenter les écarts et corrections de reproductibilité ;
- renforcer les procédures de sauvegarde/restauration ;
- garder `/diag` protégé avant toute exposition publique ;
- améliorer les runbooks d'exploitation.

## Ce que je ne fais pas encore

- Pas d'automatisation destructive.
- Pas de secrets, tokens, clés privées ou adresses sensibles dans les dépôts.
- Pas d'exposition publique de `/diag` sans authentification.
- Pas de promesse de haute disponibilité.
- Pas d'annonce de VPS réel, domaine public ou PostgreSQL finalisés tant que ce n'est pas vérifié dans le dépôt.
- Pas de prétention Kubernetes, Terraform ou cloud public enterprise dans ce portfolio.
- IA limitée à l'aide à l'analyse et à la documentation.

## Objectif professionnel

Ce profil vise des postes ou stages en :

- administration systèmes/réseaux ;
- support infrastructure ;
- exploitation Linux ;
- DevOps junior ;
- cybersécurité défensive junior.
