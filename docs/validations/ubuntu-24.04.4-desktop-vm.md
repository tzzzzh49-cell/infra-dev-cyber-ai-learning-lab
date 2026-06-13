# Validation Ubuntu 24.04.4 LTS Desktop VM

## Objectif

Ce document décrit la validation attendue du projet `infra-dev-cyber-ai-learning-lab` sur une VM Ubuntu 24.04.4 LTS Desktop. Il sert de journal reproductible pour vérifier le clone, les dépendances, les tests, Docker Compose, les diagnostics et les exports locaux.

## Environnement de test

| Élément | Valeur |
|---|---|
| Type de machine | VM locale |
| Distribution | Ubuntu 24.04.4 LTS Desktop |
| Architecture | x86_64 |
| Branche testée | `v0.3.1-ci-docs-tests` ou branche de PR équivalente |
| Version du projet | v0.3.1 de stabilisation, basée sur v0.3.0 applicatif |
| Mode de sécurité | Lecture seule |
| Exposition API | Locale uniquement, `127.0.0.1:8000` |
| Secrets requis | Aucun |

## Commandes exécutées et résultats attendus

| Étape | Commande | Résultat attendu |
|---|---|---|
| Clone | `git clone https://github.com/tzzzzh49-cell/infra-dev-cyber-ai-learning-lab.git` | Dépôt cloné sans secret local |
| Entrée dépôt | `cd infra-dev-cyber-ai-learning-lab` | Répertoire projet actif |
| Branche | `git switch <branche-de-validation>` | Branche dédiée, pas `master` |
| Bootstrap Ubuntu | `make bootstrap-ubuntu` | Prérequis installés ; reconnexion possible si le groupe Docker change |
| Validation rapide | `make check` | Lint, ShellCheck, Compose config et tests passent |
| Lint complet | `make lint` | Ruff, ShellCheck et Compose config passent |
| Tests API | `make test` | Tests pytest FastAPI et diagnostics passent |
| Compose config | `make compose-config` | Configuration Docker Compose valide |
| Build/démarrage | `make run` | Image construite, API disponible localement |
| Santé | `make health` | Réponse JSON avec `status=ok` |
| Version | `make version` | Version applicative retournée |
| Diagnostic | `make diag` | Diagnostic structuré en lecture seule |
| Export JSON | `make diag-json` | Rapport JSON créé dans `outputs/reports` |
| Export Markdown | `make diag-md` | Rapport Markdown créé dans `outputs/reports` |
| Rapports | `make reports` | Liste les rapports générés |
| Arrêt | `make down` | Conteneur arrêté proprement |
| Validation lourde | `make check-full` | Recommandée avant merge ; peut prendre plus de temps |

## Emplacement des rapports générés

Les rapports de diagnostic générés par l'API ou par les scripts locaux sont attendus dans :

```text
outputs/reports/
```

Ces rapports peuvent contenir des informations système locales. Ils ne doivent pas être publiés sans revue.

## Problèmes rencontrés

À compléter pendant une validation réelle Ubuntu :

- dépendances manquantes éventuelles ;
- besoin de reconnexion après ajout au groupe `docker` ;
- commandes indisponibles selon l'image de test (`resolvectl`, `ss`, `docker`) ;
- erreurs de permissions Docker ou SELinux/AppArmor.

Les diagnostics doivent rester robustes même si certains outils ne sont pas disponibles.

## Conclusion

Statut actuel : **partiellement validé**.

La procédure et les résultats attendus sont documentés pour Ubuntu 24.04.4 LTS Desktop. Une exécution complète sur une VM propre doit confirmer le statut **validé** avant de considérer la cible Ubuntu comme totalement approuvée.
