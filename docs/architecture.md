# Architecture du projet

## Objectif

Ce projet est un lab d’apprentissage autour de Linux, des réseaux, de Docker, de FastAPI, de l’automatisation et de la cybersécurité défensive.

L’objectif est de construire progressivement une application capable de :

- exposer une API minimale ;
- lancer des diagnostics systèmes/réseaux structurés en lecture seule ;
- produire des rapports techniques JSON et Markdown ;
- être déployée plus tard sur VPS ;
- intégrer progressivement l’API OpenAI ;
- intégrer OpenClaw de manière contrôlée.

## Architecture actuelle

```text
Utilisateur
   ↓
Makefile
   ↓
Docker Compose
   ↓
Application FastAPI
   ↓
app/main.py
   ↓
app/diagnostics.py
   ↓
Endpoints : /health, /version, /diag, /diag/export/json, /diag/export/markdown
   ↓
Rapports locaux : outputs/reports
```

## Composants

### FastAPI

FastAPI expose une API locale permettant de vérifier l’état de l’application, d'obtenir un diagnostic système/réseau structuré et de générer des exports locaux.

Endpoints actuels :

* `/` : liste les endpoints principaux ;
* `/health` : vérifie que l’application répond ;
* `/version` : affiche la version applicative ;
* `/diag` : retourne un diagnostic système/réseau structuré en lecture seule ;
* `/diag/export/json` : génère un rapport JSON horodaté dans `outputs/reports` ;
* `/diag/export/markdown` : génère un rapport Markdown horodaté dans `outputs/reports`.

### Module `app/diagnostics.py`

Le module `app/diagnostics.py` centralise la logique de diagnostic v0.3.0 :

* exécution de commandes courtes en lecture seule sans `shell=True` ;
* collecte système ;
* collecte interfaces, routes, DNS et ports ;
* collecte disque, mémoire et Docker ;
* export JSON ;
* export Markdown.

### Docker Compose

Docker Compose permet de lancer l’application dans un environnement reproductible.

Objectifs :

* éviter les différences entre machines ;
* simplifier le lancement ;
* préparer le futur déploiement VPS.

### Makefile

Le Makefile centralise les commandes utiles : validation, démarrage, endpoints, exports, diagnostics locaux et arrêt.

### Scripts

Les scripts servent à automatiser certaines tâches d’installation, de diagnostic ou de vérification.

Au stade actuel, les scripts doivent rester simples, lisibles, non destructifs et compatibles avec ShellCheck.

## Architecture cible

```text
VM Ubuntu 24.04.4 LTS Desktop
   ↓ développement, tests et validation de reproductibilité
GitHub
   ↓ versionnement puis CI plus tard
VPS Ubuntu plus tard
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

### Étape 1 — Local Ubuntu

Le projet fonctionne localement sur une VM Ubuntu 24.04.4 LTS Desktop.

Fedora 44 reste une cible secondaire utile pour vérifier la portabilité, mais la preuve principale de reproductibilité est Ubuntu.

### Étape 2 — Qualité

Ajout de tests, lint et GitHub Actions plus tard.

### Étape 3 — VPS

Déploiement futur sur VPS avec SSH sécurisé, firewall et HTTPS.

### Étape 4 — OpenAI API

Utilisation future de l’API OpenAI pour résumer les rapports et proposer des pistes d’analyse.

### Étape 5 — OpenClaw

Utilisation future d’OpenClaw avec allowlist stricte et commandes en lecture seule.

## Principes d’architecture

* commencer simple ;
* documenter chaque décision ;
* privilégier la reproductibilité ;
* limiter les droits ;
* ne pas automatiser de commandes destructives ;
* ajouter l’IA progressivement.
