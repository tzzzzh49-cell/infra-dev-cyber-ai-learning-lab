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


## Validation v0.3.0 - Diagnostic réseau avancé

Après le bootstrap et la reconnexion au groupe Docker, la validation de la version `v0.3.0` se fait avec la séquence suivante :

```bash
make check-full
make run
make diag
make diag-json
make diag-md
make diagnostic-local
make reports
make down
```

Résultats attendus :

- `make check-full` termine sans erreur et lance la validation complète du dépôt ;
- `make run` construit l’image, démarre l’application et attend que `/health` réponde ;
- `make diag` affiche un JSON contenant au minimum `metadata`, `system`, `network`, `resources`, `docker` et `security` ;
- `make diag-json` crée un rapport JSON horodaté dans `outputs/reports` ;
- `make diag-md` crée un rapport Markdown horodaté dans `outputs/reports` ;
- `make diagnostic-local` génère un rapport Markdown local et sauvegarde aussi la réponse `/diag` en JSON si l’API est démarrée ;
- `make reports` liste les rapports disponibles sans échouer si aucun rapport n’existe ;
- `make down` arrête proprement l’application Docker Compose du lab.

Si une commande de diagnostic comme `resolvectl`, `ip`, `ss` ou `docker` est absente ou indisponible, le diagnostic doit le signaler dans le rapport sans lancer de commande destructive.

## Notes de sécurité

- Aucun script de ce guide ne réalise de suppression destructrice du système ;
- les commandes de nettoyage Docker utilisées ici restent limitées au projet (`docker compose down`).
