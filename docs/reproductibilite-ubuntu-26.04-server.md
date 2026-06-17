# Reproductibilité sur Ubuntu 26.04 LTS Server

> Langues : Français | [English](reproducibility-ubuntu-26.04-server.en.md)

## Sommaire

- [Pré-requis Ubuntu Server](#pre-requis-ubuntu-server)
- [Statut de validation](#statut-de-validation)
- [Flux de validation](#1-cloner-le-depot)
- [Backups locaux Restic](#8-backups-locaux-restic)
- [Checklist Server](#checklist-server)
- [Notes de sécurité](#notes-de-securite)

Ce guide décrit le flux reproductible attendu sur une VM Ubuntu 26.04 LTS Server. La cible Ubuntu Server devient prioritaire à partir de v0.4.0.

La validation Ubuntu 24.04.4 LTS Desktop est conservée comme historique validé à 100 %. Elle ne constitue plus la cible active.

## Pré-requis Ubuntu Server

- VM Ubuntu 26.04 LTS Server à jour
- Utilisateur administrateur capable d'exécuter le bootstrap
- Accès réseau sortant vers GitHub, Docker Hub et le dépôt Docker
- Git installé ou disponible via le script de bootstrap
- Aucun secret réel dans le dépôt

## Statut de validation

Statut actuel : **procédure Server préparée, validation réelle à exécuter**.

Ne marquer Ubuntu 26.04 LTS Server comme **validé** que si la checklist du journal de validation contient les résultats réels des commandes exécutées sur une VM propre.

Journal de validation :

```text
docs/validations/ubuntu-26.04-server-vm.md
```

## 1) Cloner le dépôt

```bash
git clone https://github.com/tzzzzh49-cell/infra-dev-cyber-ai-learning-lab.git
cd infra-dev-cyber-ai-learning-lab
git switch <branche-de-validation>
```

## 2) Bootstrap système Ubuntu Server

```bash
make bootstrap-ubuntu
```

Ce script prépare les outils attendus pour le lab :

- Git, Curl, Make et Python ;
- Ansible et ShellCheck ;
- Docker Engine, Buildx et plugin Docker Compose ;
- appartenance de l'utilisateur courant au groupe `docker`.

Après exécution, se déconnecter puis se reconnecter si l'utilisateur a été ajouté au groupe `docker`.

## 3) Vérification rapide

```bash
make check
```

Résultat attendu :

- fichiers importants présents ;
- syntaxe Python valide ;
- tests pytest réussis ;
- Ruff, ShellCheck et Docker Compose config réussis ;
- aucun marqueur de conflit Git.

## 4) Validation complète

```bash
make check-full
```

Cette commande ajoute le build Docker et le playbook Ansible en mode check. Si elle n'est pas exécutée pendant une validation réelle, documenter explicitement la raison dans le journal.

## 5) Démarrage applicatif

```bash
make run
```

Résultat attendu :

- image Docker construite ;
- API démarrée via Docker Compose ;
- `/health` disponible sur l'URL locale indiquée par `.runtime/app_url`, par défaut `http://127.0.0.1:8000`.

## 6) Endpoints à vérifier

```bash
make health
make version
make diag
```

Résultats attendus :

- `make health` retourne `status=ok` ;
- `make version` retourne la version applicative ;
- `make diag` retourne un diagnostic structuré en lecture seule avec `metadata`, `system`, `network`, `resources`, `docker` et `security`.

## 7) Exports de diagnostic

```bash
make diag-json
make diag-md
make diagnostic-local
make reports
```

Résultats attendus :

- un rapport JSON horodaté est créé dans `outputs/reports` ;
- un rapport Markdown horodaté est créé dans `outputs/reports` ;
- le diagnostic local reste en lecture seule ;
- `make reports` liste les rapports sans échouer.

Les rapports peuvent contenir des informations système locales et ne doivent pas être publiés sans revue.

## 8) Backups locaux Restic

Créer un fichier privé non commité à partir de `.env.backup.example`, puis définir au minimum :

```dotenv
RESTIC_REPOSITORY=outputs/backups/restic-local
RESTIC_PASSWORD_FILE=<CHEMIN_ABSOLU_VERS_UN_FICHIER_PRIVE>
RESTIC_EXCLUDE_FILE=backup/restic-excludes.txt
```

Exécuter ensuite, uniquement après avoir vérifié les variables privées :

```bash
backup/init-local.sh
backup/backup-local.sh
backup/restore-test-local.sh
```

Résultats attendus :

- dépôt Restic local initialisé ;
- snapshot créé avec la sélection prudente du dépôt ;
- restauration de test dans `/tmp` sans écraser le dépôt courant.

## 9) Arrêt propre

```bash
make down
```

## Checklist Server

À cocher uniquement après exécution réelle sur une VM Ubuntu 26.04 LTS Server propre :

- [ ] dépôt cloné depuis GitHub ;
- [ ] branche de validation dédiée sélectionnée ;
- [ ] `make bootstrap-ubuntu` exécuté sans erreur bloquante ;
- [ ] reconnexion effectuée si l'utilisateur a été ajouté au groupe `docker` ;
- [ ] `docker --version` fonctionne sans `sudo` ;
- [ ] `docker compose version` fonctionne sans `sudo` ;
- [ ] `make check` réussi ;
- [ ] `make test` réussi ;
- [ ] `make lint` réussi ;
- [ ] `make compose-config` réussi ;
- [ ] `make check-full` réussi ou écart documenté ;
- [ ] `make run` démarre l'API sur `127.0.0.1` ;
- [ ] `make health` retourne `status=ok` ;
- [ ] `make version` retourne la version applicative ;
- [ ] `make diag` retourne un diagnostic structuré en lecture seule ;
- [ ] `make diag-json` crée un rapport JSON local ;
- [ ] `make diag-md` crée un rapport Markdown local ;
- [ ] `make diagnostic-local` génère le rapport local attendu ;
- [ ] `make reports` liste les rapports ;
- [ ] backups locaux Restic testés avec init, backup et restore drill ;
- [ ] `make down` arrête l'application proprement.

## Notes de sécurité

- Le diagnostic reste strictement en lecture seule.
- Aucun secret réel ne doit être ajouté aux exemples, scripts, rapports ou commits.
- `/diag`, `/diag/export/json` et `/diag/export/markdown` ne doivent pas être exposés publiquement sans authentification et reverse proxy HTTPS.
- En mode `APP_ENV=vps`, un token clair privé ou `DIAG_ACCESS_TOKEN_SHA256` est obligatoire ; sans configuration, les routes de diagnostic refusent l'accès.
- Préférer `DIAG_ACCESS_TOKEN_SHA256` pour éviter de stocker le token clair côté application.
- `DIAG_COMMAND_TIMEOUT` vaut `3` secondes par défaut ; augmenter seulement si la VM est lente et documenter l'écart.
- Les exemples d'appels protégés sont dans `docs/api-examples.md`.
