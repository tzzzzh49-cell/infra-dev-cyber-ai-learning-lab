# Validation Ubuntu 24.04.4 LTS Desktop VM

## Objectif

Ce document décrit la validation attendue du projet `infra-dev-cyber-ai-learning-lab` sur une VM Ubuntu 24.04.4 LTS Desktop. Il sert de journal reproductible pour vérifier le clone, les dépendances, les tests, Docker Compose, les diagnostics et les exports locaux.

Statut actuel : **validation réelle complète à finaliser**.

Ne passer le statut à **validé** que si les commandes ci-dessous ont été exécutées sur une VM Ubuntu 24.04.4 LTS Desktop propre et que les résultats observés sont renseignés.

## Environnement de test

| Élément | Valeur |
|---|---|
| Type de machine | VM locale |
| Distribution | Ubuntu 24.04.4 LTS Desktop |
| Architecture | x86_64 |
| Branche testée | `<branche-de-validation>` |
| Version du projet | v0.3.1 de stabilisation, basée sur v0.3.0 applicatif |
| Mode de sécurité | Lecture seule |
| Exposition API | Locale uniquement, `127.0.0.1:8000` |
| Secrets requis | Aucun |

## Checklist de validation

Renseigner la colonne `Résultat observé` avec `Réussi`, `Échec` ou `Non exécuté`, puis ajouter une note courte si nécessaire.

| Étape | Commande | Résultat attendu | Résultat observé | Note |
|---|---|---|---|---|
| Clone | `git clone https://github.com/tzzzzh49-cell/infra-dev-cyber-ai-learning-lab.git` | Dépôt cloné sans secret local | Non exécuté | À renseigner pendant la validation réelle |
| Entrée dépôt | `cd infra-dev-cyber-ai-learning-lab` | Répertoire projet actif | Non exécuté | À renseigner |
| Branche | `git switch <branche-de-validation>` | Branche dédiée, pas `master` | Non exécuté | À renseigner |
| Bootstrap Ubuntu | `make bootstrap-ubuntu` | Prérequis installés ; reconnexion possible si le groupe Docker change | Non exécuté | À renseigner |
| Validation rapide | `make check` | Vérifications rapides et tests passent | Non exécuté | À renseigner |
| Tests Python | `make test` | Tests pytest FastAPI et diagnostics passent | Non exécuté | À renseigner |
| Lint complet | `make lint` | Ruff, ShellCheck et Compose config passent | Non exécuté | À renseigner |
| Compose config | `make compose-config` | Configuration Docker Compose valide | Non exécuté | À renseigner |
| Validation lourde | `make check-full` | Recommandée avant merge ; peut prendre plus de temps | Non exécuté | Documenter si non exécuté |
| Build/démarrage | `make run` | Image construite, API disponible localement | Non exécuté | À renseigner |
| Santé | `make health` | Réponse JSON avec `status=ok` | Non exécuté | À renseigner |
| Version | `make version` | Version applicative retournée | Non exécuté | À renseigner |
| Diagnostic | `make diag` | Diagnostic structuré en lecture seule | Non exécuté | À renseigner |
| Export JSON | `make diag-json` | Rapport JSON créé dans `outputs/reports` | Non exécuté | À renseigner |
| Export Markdown | `make diag-md` | Rapport Markdown créé dans `outputs/reports` | Non exécuté | À renseigner |
| Diagnostic local | `make diagnostic-local` | Rapport local généré en lecture seule | Non exécuté | À renseigner |
| Rapports | `make reports` | Liste les rapports générés | Non exécuté | À renseigner |
| Arrêt | `make down` | Conteneur arrêté proprement | Non exécuté | À renseigner |

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

Statut actuel : **validation réelle complète à finaliser**.

La procédure et les résultats attendus sont documentés pour Ubuntu 24.04.4 LTS Desktop. Une exécution complète sur une VM propre doit confirmer le statut **validé** avant de considérer la cible Ubuntu comme totalement approuvée.
