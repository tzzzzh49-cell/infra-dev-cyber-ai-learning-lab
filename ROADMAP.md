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
- ne pas ajouter Caddy, Restic, PostgreSQL, OpenAI API, OpenClaw, Containerlab, déploiement VPS ou authentification ;
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
- `AGENTS.md` complété avec règles de sécurité et workflow agents ;
- tests API FastAPI renforcés ;
- tests unitaires diagnostics complétés ;
- documentation Ubuntu Desktop historique complétée ;
- préparation documentaire VPS et backups sans déploiement réel ;
- durcissement léger de l'image applicative Docker.

Limites :
- pas de déploiement VPS réel ;
- pas d'authentification applicative ;
- pas d'intégration OpenAI API ;
- pas d'intégration OpenClaw.

## v0.4.0 - Ubuntu Server, VPS et backups

Objectif : préparer la cible prioritaire Ubuntu 26.04 LTS Server, le futur VPS sécurisé et la stratégie de sauvegarde sans déploiement réel.

Prévu / en préparation :
- documentation de reproductibilité Ubuntu 26.04 LTS Server ;
- journal de validation `docs/validations/ubuntu-26.04-server-vm.md` ;
- checklist Server : clone, bootstrap, reconnexion Docker, `make check`, `make check-full`, `make run`, endpoints, exports et backups locaux ;
- procédure VPS ordonnée : première connexion, utilisateur non-root, SSH, firewall, Docker, Compose, Caddy HTTPS, Cloudflare DNS et variables `.env.vps.example` ;
- exemples sûrs `docs/vps/Caddyfile.example` et `docs/vps/compose.vps.example.yaml` ;
- stratégie Restic local-first étendue vers S3-compatible avec placeholders uniquement ;
- documentation init, backup, check et restore drill ;
- contrôles CI sécurité non secrets : Bandit, Hadolint et Trivy.

Limites :
- pas de déploiement VPS réel ;
- pas d'adresse IP, domaine, token, clé privée ou mot de passe réel ;
- `/diag` reste protégé en mode `APP_ENV=vps` par `DIAG_ACCESS_TOKEN` et reverse proxy authentifié.

## v0.5.0 - OpenAI API read-only

Objectif : préparer une intégration OpenAI API limitée au résumé de rapports sans appel réel obligatoire.

Prévu :
- structure `docs/ai/` et `app/ai/` ;
- fichier `.env.ai.example` sans clé réelle ;
- flux documentaire rapport Markdown/JSON -> résumé -> risques -> checklist ;
- budget limité et clé uniquement via variable d'environnement ;
- aucune exécution de commande, aucune modification système, aucune lecture volontaire de secrets.

## v0.6.0 - OpenClaw contrôlé

Objectif : préparer OpenClaw comme couche documentaire et contrôlée, non active par défaut.

Prévu :
- structure `openclaw/` avec allowlist, runbooks et modèle de sécurité ;
- mode lecture seule ;
- refus explicite de `sudo`, suppressions, modifications réseau, actions Docker destructives et commandes automatiques sans validation humaine ;
- sandbox et validation humaine avant tout futur usage.
