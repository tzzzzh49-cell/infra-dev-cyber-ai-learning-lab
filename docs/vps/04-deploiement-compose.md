# 04 - Déploiement Docker Compose

Objectif : préparer le futur lancement Compose sans l'effectuer dans cette tâche.

Recommandations :

- cloner le dépôt sur le VPS avec une branche/tag validé ;
- garder `APP_HOST=127.0.0.1` pour ne pas exposer l'API directement ;
- définir `APP_ENV=vps` dans un fichier `.env` privé ;
- définir `DIAG_ACCESS_TOKEN` dans ce même fichier privé avant toute exposition via reverse proxy ;
- monter `outputs/` pour conserver les rapports ;
- vérifier `make compose-config` avant démarrage ;
- lancer l'application seulement après revue de la configuration.

Configuration attendue côté application :

```dotenv
APP_ENV=vps
APP_HOST=127.0.0.1
APP_PORT=8000
DIAG_ACCESS_TOKEN=<TOKEN_PRIVE_HORS_GIT>
```

`/diag`, `/diag/export/json` et `/diag/export/markdown` peuvent contenir des informations système : ne jamais les exposer publiquement sans authentification, reverse proxy HTTPS et token applicatif.

Le reverse proxy doit joindre l'application sur `127.0.0.1:8000`. Ne pas publier directement le port FastAPI sur une interface publique.
