# Architecture du projet

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

```text
Utilisateur
   ↓
Makefile
   ↓
Docker Compose
   ↓
Application FastAPI
   ↓
Endpoints : /health, /version, /diag
```

## Composants

### FastAPI

FastAPI expose une API simple permettant de vérifier l’état de l’application et de lancer des diagnostics contrôlés.

Endpoints actuels :

* `/health` : vérifie que l’application répond ;
* `/version` : affiche la version ou des informations de base ;
* `/diag` : lance ou affiche un diagnostic simple.

### Docker Compose

Docker Compose permet de lancer l’application dans un environnement reproductible.

Objectifs :

* éviter les différences entre machines ;
* simplifier le lancement ;
* préparer le futur déploiement VPS.

### Makefile

Le Makefile sert d’interface de commande simple.

Exemples :

```bash
make build
make up
make health
make version
make diag
make down
```

### Scripts

Les scripts servent à automatiser certaines tâches d’installation, de diagnostic ou de vérification.

Au stade actuel, les scripts doivent rester simples, lisibles et non destructifs.

## Architecture cible

```text
VM Ubuntu 24.04.4 LTS Desktop
   ↓ développement, tests et validation de reproductibilité
GitHub
   ↓ versionnement puis CI plus tard
VPS Ubuntu
   ↓ Docker Compose
Application FastAPI
   ↓
Diagnostics systèmes/réseaux en lecture seule
   ↓
Rapports Markdown / JSON plus tard
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
