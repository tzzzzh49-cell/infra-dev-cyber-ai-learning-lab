# 04 - Déploiement Docker Compose

Objectif : préparer le futur lancement Compose sans l'effectuer dans cette tâche.

Recommandations :

- cloner le dépôt sur le VPS avec une branche/tag validé ;
- garder `APP_HOST=127.0.0.1` pour ne pas exposer l'API directement ;
- monter `outputs/` pour conserver les rapports ;
- vérifier `make compose-config` avant démarrage ;
- lancer l'application seulement après revue de la configuration.

`/diag` peut contenir des informations système : ne jamais l'exposer publiquement sans authentification.
