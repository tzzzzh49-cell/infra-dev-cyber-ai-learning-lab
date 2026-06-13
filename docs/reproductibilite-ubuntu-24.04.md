# Reproductibilité sur Ubuntu 24.04.4 LTS

Ce guide décrit le flux reproductible attendu sur une VM Ubuntu 24.04.4 LTS Desktop. La cible Ubuntu reste prioritaire, mais ce document ne suffit pas à prouver une validation réelle : les résultats doivent être rejoués et consignés dans `docs/validations/ubuntu-24.04.4-desktop-vm.md`.

## Pré-requis Ubuntu

- VM Ubuntu 24.04.4 LTS à jour
- Utilisateur avec droits `sudo`
- Accès réseau sortant (GitHub + Docker Hub + dépôt Docker)
- Git installé (sinon via le script de bootstrap)

## Statut de validation

Statut actuel : **validation réelle complète à finaliser**.

La procédure est documentée et prête à être exécutée. Ne marquer Ubuntu comme **validé** que si la checklist du journal de validation contient les résultats réels des commandes exécutées sur une VM Ubuntu 24.04.4 LTS Desktop propre.

Journal de validation :

`docs/validations/ubuntu-24.04.4-desktop-vm.md`

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

## 7) Validation v0.3.0 - Diagnostic réseau avancé

Exécuter la séquence suivante sur Ubuntu 24.04.4 LTS Desktop :

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

- `make check-full` réussit les tests Python, Ruff, ShellCheck, Docker Compose config, le build Docker et Ansible en mode check ;
- `make run` démarre l'application et attend que `/health` réponde ;
- `make diag` retourne un JSON contenant au minimum `metadata`, `system`, `network`, `resources`, `docker` et `security` ;
- `make diag-json` crée un rapport JSON horodaté dans `outputs/reports` ;
- `make diag-md` crée un rapport Markdown horodaté dans `outputs/reports` ;
- `make diagnostic-local` crée un rapport Markdown local et sauvegarde la réponse JSON de `/diag` si l'API est disponible ;
- `make reports` liste les rapports générés sans échouer ;
- `make down` arrête proprement l'application.

## Checklist de validation Ubuntu

À cocher uniquement après exécution réelle sur une VM Ubuntu 24.04.4 LTS Desktop propre :

- [ ] `make bootstrap-ubuntu` exécuté sans erreur bloquante ;
- [ ] reconnexion effectuée si l'utilisateur a été ajouté au groupe `docker` ;
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
- [ ] `make down` arrête l'application proprement.

## 8) Arrêt propre

```bash
make down
```

## Notes de sécurité

- Aucun script de ce guide ne réalise de suppression destructrice du système ;
- les commandes de nettoyage Docker utilisées ici restent limitées au projet (`docker compose down`).
