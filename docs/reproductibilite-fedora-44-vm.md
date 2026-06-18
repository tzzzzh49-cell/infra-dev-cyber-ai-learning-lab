# Reproductibilité sur Fedora 44 Workstation VM

Ce guide décrit un flux reproductible **validé/à valider uniquement pour Fedora 44 Workstation VM**.

## Pré-requis Fedora

- VM Fedora 44 Workstation à jour
- Utilisateur avec droits `sudo`
- Accès réseau sortant (GitHub + Docker Hub + dépôt Docker)
- Git installé (sinon via le script de bootstrap)

## 1) Cloner le dépôt

```bash
git clone https://github.com/tzzzzh49-cell/infra-dev-cyber-ai-learning-lab.git
cd infra-dev-cyber-ai-learning-lab
```

## 2) Bootstrap système Fedora

```bash
BOOTSTRAP_CONFIRM=yes make bootstrap-fedora
```

Ce script :
- met à jour Fedora ;
- installe les outils nécessaires (`git`, `curl`, `make`, `python3`, `ansible`, `shellcheck`, etc.) ;
- installe Docker Engine + plugin Docker Compose ;
- active le service Docker ;
- ajoute l'utilisateur courant au groupe `docker`.

> Après exécution : **se déconnecter/reconnecter** à la session pour appliquer le groupe `docker`.

## 3) Vérifier rapidement l'environnement

```bash
make check
```

## 4) Build et démarrage

```bash
make build
make up
```

## 5) Vérifier les endpoints de l'API

```bash
make health
make version
make diag
```

## 6) Validation complète

```bash
make check-full
```

Cette commande lance aussi un build Docker et le playbook Ansible en mode check.

## 7) Arrêt propre

```bash
make down
```

## Validation finale du mois 1

Date : 2026-05-26
Environnement : Fedora 44 Workstation VM  
Branche testée : master  
Version prévue : v0.1.0

### Objectif

Vérifier que le projet peut être cloné, lancé et testé depuis une installation propre.

### Commandes exécutées

```bash
git clone https://github.com/tzzzzh49-cell/infra-dev-cyber-ai-learning-lab.git
cd infra-dev-cyber-ai-learning-lab
make help
make build
make up
make health
make version
make diag
make down
```

### Résultat

La reproduction fonctionne après correction du chemin du script Fedora dans le `Makefile`.

Le `Makefile` utilise désormais :

```bash
./scripts/bootstrap_fedora44_vm.sh
```

### Points vérifiés

- Le dépôt se clone correctement ;
- Docker Compose construit l'application ;
- l'application démarre ;
- `/health` répond ;
- `/version` répond ;
- `/diag` répond ;
- l'application peut être arrêtée proprement.

### Problème rencontré

Une incohérence existait entre le `Makefile` local corrigé et la version présente sur GitHub.

### Correction

La branche contenant la correction a été intégrée dans `master`.

### Leçon apprise

Un projet peut fonctionner localement tout en étant différent de la version visible sur GitHub.

Il faut donc vérifier :

- la branche courante ;
- les commits locaux ;
- les commits distants ;
- le résultat après `push` ;
- le contenu réel affiché sur GitHub.

## Notes de sécurité

- Aucun script de ce guide ne réalise de suppression destructrice du système ;
- les commandes de nettoyage Docker utilisées ici restent limitées au projet (`docker compose down`).
