# Roadmap

## v0.1.0 - Reproduction locale stable

Objectif : stabiliser la base locale du projet.

Inclus :
- API FastAPI minimale ;
- Docker Compose fonctionnel ;
- Makefile utilisable ;
- documentation initiale ;
- reproduction Fedora 44 validée ;
- première cible Ubuntu Desktop historique documentée ;
- règles de sécurité en lecture seule.

## v0.2.0 - Cohérence, sécurité locale et préparation Ubuntu/CI

Objectif : livrer une base cohérente, sécurisée localement et préparée pour la première validation Ubuntu Desktop historique.

Inclus :
- rendre le dépôt cohérent avec son nom actuel `infra-dev-cyber-ai-learning-lab` ;
- nettoyer les noms historiques quand ils désignent le projet actuel ;
- sécuriser la configuration locale avec une exposition par défaut sur `127.0.0.1` ;
- ajouter un exemple d'environnement VPS sans secret et sans exposition directe de `/diag` ;
- préparer la validation réelle sur Ubuntu Desktop ;
- préparer la future CI GitHub Actions sans créer encore de workflow ;
- garder le projet en mode lecture seule, sans commande destructive et sans secret.

Limites de cette étape :
- ne pas ajouter GitHub Actions ;
- ne pas ajouter de reverse proxy, Restic, PostgreSQL, Containerlab, déploiement VPS ou authentification ;
- ne pas ajouter de nouvelles grosses fonctionnalités applicatives.

Note historique : la reproductibilité sur Ubuntu 24.04.4 LTS Desktop a ensuite été validée à 100 % et sert de référence passée, pas de cible active.

## v0.3.0 - Diagnostic réseau avancé

Objectif : enrichir le diagnostic système/réseau.

Inclus / livré :
- collecte des interfaces réseau ;
- collecte des routes ;
- collecte DNS via `/etc/resolv.conf` et `resolvectl` si disponible ;
- collecte des ports ouverts ;
- collecte disque ;
- collecte mémoire ;
- collecte Docker via `docker ps` en lecture seule ;
- export JSON dans `outputs/reports` ;
- export Markdown dans `outputs/reports` ;
- tests API et diagnostics ;
- documentation dédiée du diagnostic réseau avancé.

## v0.3.1 - Qualité, CI et documentation de préparation VPS

Objectif : stabiliser le dépôt avant la préparation v0.4.0 VPS.

Inclus / livré :
- CI GitHub Actions minimale sans secret ;
- tests API FastAPI renforcés ;
- tests unitaires diagnostics complétés ;
- documentation Ubuntu Desktop historique complétée ;
- préparation documentaire VPS et backups sans déploiement réel ;
- durcissement léger de l'image applicative Docker.

Limites :
- pas de déploiement VPS réel ;
- pas d'authentification applicative.

## v0.3.2 - Durcissement Docker, diagnostics configurables et documentation

Objectif : corriger la construction d'image, réduire l'exposition dans les
couches Docker et clarifier les choix de sécurité avant v0.4.0.

Inclus / livré :
- build Docker multi-étapes avec dépendances runtime issues uniquement de `app/requirements.txt` ;
- runtime non-root explicite `10001:10001` ;
- contexte Compose corrigé pour copier `app/requirements.txt` sans contournement ;
- copies Docker séparées pour l'application et les exemples de configuration ;
- `.dockerignore` pour exclure sorties, environnements locaux, tests et secrets ;
- timeout de diagnostic configurable via `DIAG_COMMAND_TIMEOUT`, par défaut `3` secondes ;
- tentatives bornées via `DIAG_COMMAND_RETRIES`, désactivées par défaut ;
- protection locale des diagnostics par hash `DIAG_ACCESS_TOKEN_HASH` avec jeton client transmis via `Authorization` ou `X-Diag-Token` ;
- script `scripts/generate_diag_token.py` et tests associés ;
- documentation bilingue initiale pour architecture, sécurité et reproductibilité Ubuntu Server ;
- sommaire principal `docs/README.md` ;
- exemples `curl` protégés dans `docs/api-examples.md`.

Limites :
- Postgres reste préparatoire via le profil Compose `future-persistence`, non lancé par défaut ;
- aucune migration n'est active tant qu'une dépendance et un outil comme Alembic ne sont pas validés ;
- aucun middleware CORS n'est activé tant qu'il n'existe pas de consommateur front séparé.

## v0.4.0 - Ubuntu Server, VPS et backups

Objectif : préparer la cible prioritaire Ubuntu 26.04 LTS Server, le futur VPS sécurisé et la stratégie de sauvegarde sans déploiement réel.

Prévu / en préparation :
- documentation de reproductibilité Ubuntu 26.04 LTS Server ;
- journal de validation `docs/validations/ubuntu-26.04-server-vm.md` ;
- checklist Server : clone, bootstrap, reconnexion Docker, `make check`, `make check-full`, `make run`, endpoints, exports et backups locaux ;
- procédure VPS ordonnée : première connexion, utilisateur non-root, SSH, firewall, Docker, Compose, Nginx HTTPS, Cloudflare DNS et variables `.env.vps.example` ;
- exemples sûrs `docs/vps/nginx.reverse-proxy.example.conf` et `docs/vps/compose.vps.example.yaml` ;
- stratégie Restic local-first étendue vers S3-compatible avec placeholders uniquement ;
- documentation init, backup, check et restore drill ;
- politique mensuelle de mise à jour des dépendances ;
- contrôles sécurité locaux et CI non secrets : Bandit, Hadolint et Trivy ;
- préparation Postgres, migrations et stockage de rapports revus, sans activation automatique.

Limites :
- pas de déploiement VPS réel ;
- pas d'adresse IP, domaine, token, clé privée ou mot de passe réel ;
- `/diag` reste protégé en mode `APP_ENV=vps` par OAuth2/OIDC, RBAC applicatif et reverse proxy authentifié.
