# Validation Ubuntu 24.04.4 LTS Desktop VM

## Objectif

Ce document prouve que le projet `infra-dev-cyber-ai-learning-lab` a été testé sur une VM Ubuntu 24.04.4 LTS Desktop.

L'objectif est de vérifier que le dépôt peut être cloné, préparé, testé, lancé, diagnostiqué et arrêté proprement sur Ubuntu 24.04.4 LTS Desktop.

## Environnement de test

| Élément | Valeur |
|---|---|
| Type de machine | VM locale |
| Distribution | Ubuntu 24.04.4 LTS Desktop |
| Architecture | x86_64 |
| Branche testée | master |
| Version du projet | v0.2.0 en préparation |
| Mode de sécurité | Lecture seule |
| Exposition API | Locale uniquement, 127.0.0.1:8000 |

## Commandes exécutées

### 1. Clone du dépôt

```bash
git clone https://github.com/tzzzzh49-cell/infra-dev-cyber-ai-learning-lab.git
cd infra-dev-cyber-ai-learning-lab
