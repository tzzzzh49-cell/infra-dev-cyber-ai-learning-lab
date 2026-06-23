# Architecture du projet

> Langues : Français | [English](architecture.en.md)

## Sommaire

- [Objectif](#objectif)
- [Architecture actuelle](#architecture-actuelle)
- [Composants](#composants)
- [Choix Docker et Compose](#choix-docker-et-compose)
- [Persistance préparatoire](#persistance-preparatoire)
- [Évolutions prévues](#evolution-prevue)
- [Principes d'architecture](#principes-darchitecture)

## Objectif

Ce projet est un lab d’apprentissage autour de Linux, des réseaux, de Docker, de FastAPI, de l’automatisation et de la cybersécurité défensive.

L’objectif est de construire progressivement une application capable de :

- exposer une API minimale ;
- lancer des diagnostics systèmes/réseaux en lecture seule ;
- produire des rapports techniques ;
- être déployée plus tard sur VPS ;
- intégrer progressivement l’API OpenAI ;
- intégrer OpenClaw de manière contrôlée.

## Architecture actuelle

```mermaid
flowchart TD
    user[Utilisateur local] --> make[Makefile]
    browser[Utilisateur VPS] --> nginx[Nginx HTTPS<br/>ModSecurity + OWASP CRS]
    nginx -. auth_request .-> oauth[OAuth2 Proxy<br/>Authorization Code + PKCE]
    oauth <--> idp[Fournisseur OIDC<br/>MFA et anti-bruteforce]
    nginx -- mTLS --> api
    make --> compose[Docker Compose]
    compose --> api[Application FastAPI]
    api --> main[app/main.py]
    main --> auth[OIDC JWT + RBAC<br/>token local en mode lab]
    auth --> diagnostics[app/diagnostics.py]
    diagnostics --> allowlist[Allowlist commandes read-only<br/>timeout + logging]
    allowlist --> reports[outputs/reports<br/>JSON et Markdown]
    diagnostics --> logs[outputs/logs/app.log]
    make --> localdiag[scripts/diagnostic_local.sh]
    localdiag --> api
    localdiag --> reports
    make --> backups[backup/*.sh]
    backups --> backupstore[outputs/backups<br/>Restic local-first]
```

Flux principal :

1. `Makefile` orchestre les commandes locales.
2. Docker Compose démarre l'API sur `127.0.0.1`.
3. `app/main.py` protège les routes `/diag` par OIDC/RBAC en VPS et conserve le
   hash de jeton uniquement pour le lab local.
4. `app/diagnostics.py` exécute uniquement les commandes read-only allowlistées.
5. Les rapports sont écrits dans `outputs/reports` et les logs dans `outputs/logs`.
6. Les scripts de backup Restic restent séparés des diagnostics API.

## Composants

### FastAPI

FastAPI expose une API simple permettant de vérifier l’état de l’application et de lancer des diagnostics contrôlés.

Endpoints actuels :

* `/health` : vérifie que l’application répond ;
* `/version` : affiche la version applicative ;
* `/diag` : retourne un état système/réseau minimisé en lecture seule ;
* `/diag/export/json` : génère un rapport JSON local ;
* `/diag/export/markdown` : génère un rapport Markdown local.

### Module `app/diagnostics.py`

Le module `app/diagnostics.py` centralise la collecte de diagnostic avancé. Il utilise uniquement la bibliothèque standard Python, exécute les commandes sans `shell=True`, applique des timeouts courts et gère les commandes absentes sans exception non contrôlée.

Il collecte :

* informations système ;
* interfaces réseau ;
* routes ;
* DNS ;
* ports ouverts ;
* disque ;
* mémoire ;
* état Docker en lecture seule.

Il produit également les exports JSON et Markdown dans `outputs/reports`. Un
verrou global empêche les diagnostics concurrents et chaque format conserve ses
20 exports les plus récents.

Le module journalise les commandes lancées, les commandes absentes, les timeouts et l'écriture des rapports via la bibliothèque `logging`. Le fichier par défaut est `outputs/logs/app.log`, ignoré par Git.

### Docker Compose

Docker Compose permet de lancer l’application dans un environnement reproductible.

Objectifs :

* éviter les différences entre machines ;
* simplifier le lancement ;
* préparer le futur déploiement VPS.

## Choix Docker et Compose

L'image applicative utilise un build multi-étapes :

* l'étape `builder` installe uniquement les dépendances runtime depuis
  `app/requirements.txt` dans un environnement virtuel ;
* l'étape `runtime` copie uniquement cet environnement et le code applicatif ;
* le code reste propriétaire de root et le conteneur s'exécute avec l'utilisateur non-root `10001:10001`.

Le non-root limite l'impact d'une faille applicative : même si l'API est
compromise, le processus ne doit pas disposer de privilèges root dans le
conteneur. Compose répète ce choix avec `user: "10001:10001"` pour rendre le
contrat visible pendant la revue. Le système de fichiers racine est en lecture
seule, toutes les capacités Linux sont retirées et `no-new-privileges` est actif.

Les seuls montages en écriture sont `./outputs/reports` et `./outputs/logs`.
`outputs/raw`, `outputs/backups`, le dépôt complet, les fichiers `.env` et les
secrets locaux ne sont pas montés dans le conteneur.

`restart: unless-stopped` est utilisé pour simuler un comportement VPS réaliste :
le service revient après un redémarrage Docker, mais un arrêt explicite par
`make down` ou `docker compose down` reste respecté.

Les logs applicatifs restent dirigés vers stdout/stderr. Docker ou le futur VPS
peuvent ensuite les collecter avec le driver de logs standard, un sidecar ou un
agent externe. Le projet ne doit pas écrire de fichiers de logs applicatifs
persistants contenant des données sensibles.

## Persistance préparatoire

La persistance n'est pas active dans l'application v0.3.x. Compose prépare
toutefois un profil `future-persistence` avec un service Postgres et le volume
`postgres_data`. Ce profil est inactif par défaut.

Avant activation réelle, il faudra ajouter :

* une dépendance applicative PostgreSQL explicitement revue ;
* une gestion de migrations, par exemple Alembic ;
* une politique de rétention des rapports ;
* un stockage dédié ou externe pour les rapports IA revus.

Le volume `ai_reports` est réservé comme point de préparation. Aucun rapport IA
n'est généré automatiquement dans l'état actuel.

## CORS futur

Aucun middleware CORS n'est activé aujourd'hui, car l'API est consommée
localement et ne sert pas encore de backend public pour un front. Si un front
local ou un service IA séparé consomme l'API, les origines devront être listées
explicitement via une variable du type `CORS_ALLOWED_ORIGINS`, sans wildcard en
mode VPS.

### Makefile

Le Makefile sert d’interface de commande simple.

Exemples :

```bash
make build
make up
make health
make version
make diag
make diag-json
make diag-md
make reports
make down
```

### Scripts

Les scripts servent à automatiser certaines tâches d’installation, de diagnostic ou de vérification.

Le script `scripts/diagnostic_local.sh` génère un rapport Markdown local en lecture seule et sauvegarde aussi la réponse JSON de `/diag` dans `outputs/reports` si l’API est disponible.

## Architecture cible

```text
VM Ubuntu 26.04 LTS Server
   ↓ développement, tests et validation de reproductibilité prioritaire
GitHub
   ↓ versionnement puis CI plus tard
VPS Ubuntu
   ↓ Docker Compose
Application FastAPI
   ↓
Diagnostics systèmes/réseaux en lecture seule
   ↓
Rapports Markdown / JSON disponibles localement
   ↓
Résumé IA via OpenAI API plus tard
   ↓
Interaction contrôlée via OpenClaw plus tard
```

## Évolution prévue

### Étape 1 — Local Ubuntu Server

Le projet cible prioritairement une VM Ubuntu 26.04 LTS Server.

Fedora 44 reste une cible secondaire utile pour vérifier la portabilité. Ubuntu 24.04.4 LTS Desktop est conservée comme historique validé à 100 %.

### Étape 2 — Qualité

Ajout de tests, lint et GitHub Actions.

### Étape 3 — VPS

Déploiement sur VPS avec SSH sécurisé, firewall et HTTPS.

### Étape 4 — OpenAI API

Utilisation de l’API OpenAI pour résumer les rapports et proposer des pistes d’analyse.

### Étape 5 — OpenClaw

Utilisation d’OpenClaw avec allowlist stricte et commandes en lecture seule.

## Principes d’architecture

* commencer simple ;
* documenter chaque décision ;
* privilégier la reproductibilité ;
* limiter les droits ;
* ne pas automatiser de commandes destructives ;
* ajouter l’IA progressivement.
