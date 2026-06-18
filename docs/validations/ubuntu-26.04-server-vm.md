# Validation Ubuntu 26.04 LTS Server VM

## Objectif

Ce document sert de journal reproductible pour vérifier le clone, le bootstrap, les tests, Docker Compose, les diagnostics, les exports et les backups locaux sur une VM Ubuntu 26.04 LTS Server.

Statut actuel : **procédure préparée, validation réelle à exécuter**.

La validation Ubuntu 24.04.4 LTS Desktop est historique et validée à 100 %. Ce journal concerne la nouvelle cible prioritaire Server.

Ne passer le statut Ubuntu 26.04 Server à **validé** que si les commandes ci-dessous ont été exécutées sur une VM propre et que les résultats observés sont renseignés.

## Environnement de test

| Élément | Valeur |
|---|---|
| Type de machine | VM locale |
| Distribution | Ubuntu 26.04 LTS Server |
| Architecture | x86_64 |
| Branche testée | `<branche-de-validation>` |
| Version du projet | v0.3.2 de durcissement, préparation v0.4.0 Server/VPS/backups |
| Mode de sécurité | Lecture seule pour les diagnostics |
| Exposition API | Locale uniquement, `127.0.0.1:8000` |
| Secrets requis | Aucun secret réel dans le dépôt |

## Checklist de validation

Renseigner la colonne `Résultat observé` avec `Réussi`, `Échec` ou `Non exécuté`, puis ajouter une note courte si nécessaire.

| Étape | Commande | Résultat attendu | Résultat observé | Note |
|---|---|---|---|---|
| Clone | `git clone https://github.com/tzzzzh49-cell/infra-dev-cyber-ai-learning-lab.git` | Dépôt cloné sans secret local | Non exécuté | À renseigner |
| Entrée dépôt | `cd infra-dev-cyber-ai-learning-lab` | Répertoire projet actif | Non exécuté | À renseigner |
| Branche | `git switch <branche-de-validation>` | Branche dédiée, pas `master` | Non exécuté | À renseigner |
| Bootstrap Ubuntu Server | `BOOTSTRAP_CONFIRM=yes make bootstrap-ubuntu` | Prérequis installés ; reconnexion possible si le groupe Docker change | Non exécuté | À renseigner |
| Reconnexion Docker | `docker ps` | Docker utilisable sans `sudo` après reconnexion | Non exécuté | À renseigner |
| Compose plugin | `docker compose version` | Plugin Docker Compose disponible | Non exécuté | À renseigner |
| Validation rapide | `make check` | Vérifications rapides et tests passent | Non exécuté | À renseigner |
| Tests Python | `make test` | Tests pytest FastAPI et diagnostics passent | Non exécuté | À renseigner |
| Lint complet | `make lint` | Ruff, ShellCheck et Compose config passent | Non exécuté | À renseigner |
| Compose config | `make compose-config` | Configuration Docker Compose valide | Non exécuté | À renseigner |
| Validation lourde | `make check-full` | Build Docker et Ansible check passent | Non exécuté | Documenter si non exécuté |
| Build/démarrage | `make run` | Image construite, API disponible localement | Non exécuté | À renseigner |
| Santé | `make health` | Réponse JSON avec `status=ok` | Non exécuté | À renseigner |
| Version | `make version` | Version applicative retournée | Non exécuté | À renseigner |
| Diagnostic | `make diag` | Diagnostic structuré en lecture seule | Non exécuté | À renseigner |
| Export JSON | `make diag-json` | Rapport JSON créé dans `outputs/reports` | Non exécuté | À renseigner |
| Export Markdown | `make diag-md` | Rapport Markdown créé dans `outputs/reports` | Non exécuté | À renseigner |
| Diagnostic local | `make diagnostic-local` | Rapport local généré en lecture seule | Non exécuté | À renseigner |
| Rapports | `make reports` | Liste les rapports générés | Non exécuté | À renseigner |
| Restic init local | `backup/init-local.sh` | Dépôt local initialisé avec passphrase hors Git | Non exécuté | À renseigner |
| Restic backup local | `backup/backup-local.sh` | Snapshot local créé avec exclusions prudentes | Non exécuté | À renseigner |
| Restic restore drill | `backup/restore-test-local.sh` | Restauration de test sous `/tmp` | Non exécuté | À renseigner |
| Arrêt | `make down` | Conteneur arrêté proprement | Non exécuté | À renseigner |

## Emplacement des rapports générés

Les rapports de diagnostic générés par l'API ou par les scripts locaux sont attendus dans :

```text
outputs/reports/
```

Ces rapports peuvent contenir des informations système locales. Ils ne doivent pas être publiés sans revue.

## Emplacement des backups locaux

Le dépôt Restic local de test est attendu par défaut dans :

```text
outputs/backups/restic-local
```

La passphrase doit rester dans un fichier privé hors dépôt via `RESTIC_PASSWORD_FILE`.

## Problèmes rencontrés

À compléter pendant une validation réelle Ubuntu Server :

- dépendances manquantes éventuelles ;
- besoin de reconnexion après ajout au groupe `docker` ;
- commandes indisponibles selon l'image de test (`resolvectl`, `ss`, `docker`) ;
- erreurs de permissions Docker, AppArmor ou réseau sortant ;
- écart volontaire si `make check-full` n'est pas exécuté.

Les diagnostics doivent rester robustes même si certains outils ne sont pas disponibles.

## Conclusion

Statut actuel : **procédure préparée, validation réelle à exécuter**.

Une exécution complète sur une VM Ubuntu 26.04 LTS Server propre doit confirmer le statut **validé** avant de considérer la nouvelle cible prioritaire comme approuvée.
