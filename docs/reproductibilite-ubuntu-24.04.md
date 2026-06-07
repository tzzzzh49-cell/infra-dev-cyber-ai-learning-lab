# Reproductibilité sur Ubuntu 24.04.4 LTS

Ce guide décrit un flux reproductible validé sur une VM Ubuntu 24.04.4 LTS Desktop.

## Pré-requis Ubuntu

- VM Ubuntu 24.04.4 LTS à jour
- Utilisateur avec droits `sudo`
- Accès réseau sortant (GitHub + Docker Hub + dépôt Docker)
- Git installé (sinon via le script de bootstrap)

## Validation réelle

Une validation réelle a été effectuée sur une VM Ubuntu 24.04.4 LTS Desktop.

Rapport de validation :

docs/validations/ubuntu-24.04.4-desktop-vm.md

## 1) Cloner le dépôt

```bash
git clone https://github.com/tzzzzh49-cell/infra-dev-cyber-ai-learning-lab.git
cd infra-dev-cyber-ai-learning-lab
```

## 2) Bootstrap système Ubuntu

```bash
make bootstrap-ubuntu
```

Ce script :
- met à jour l'index APT ;
- installe les outils nécessaires (`git`, `curl`, `make`, `python3`, `ansible`, `shellcheck`, etc.) ;
- installe Docker Engine + plugin Docker Compose depuis le dépôt Docker officiel ;
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

## Notes de sécurité

- Aucun script de ce guide ne réalise de suppression destructrice du système ;
- les commandes de nettoyage Docker utilisées ici restent limitées au projet (`docker compose down`).
