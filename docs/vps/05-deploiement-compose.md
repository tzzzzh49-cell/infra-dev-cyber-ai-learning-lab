# 04 - Déploiement Docker Compose

Objectif : préparer le futur lancement Compose sans l'effectuer dans cette tâche.

Recommandations :

- cloner le dépôt sur le VPS avec une branche/tag validé ;
- garder `APP_HOST=127.0.0.1` pour ne pas exposer l'API directement ;
- définir `APP_ENV=vps` dans un fichier `.env` privé ;
- définir `DIAG_ACCESS_TOKEN_HASH` via un gestionnaire de secrets, Vault Agent, AWS Secrets Manager ou un fichier monté privé ;
- garder le token clair hors de l'application ; il sert seulement au client ou au reverse proxy de confiance ;
- monter `outputs/` pour conserver les rapports ;
- vérifier `make compose-config` avant démarrage ;
- lancer l'application seulement après revue de la configuration.
- utiliser `docs/vps/compose.vps.example.yaml` comme exemple de structure, pas comme configuration finale non relue.

Configuration attendue côté application :

```dotenv
APP_ENV=vps
APP_HOST=127.0.0.1
APP_PORT=8000
DIAG_ACCESS_TOKEN_HASH=<HASH_DEPUIS_GESTIONNAIRE_DE_SECRETS>
DIAG_ACCESS_TOKEN_HASH_FILE=
DIAG_PROTECTION_DISABLED=false
LAB_DOMAIN=<LAB_DOMAIN>
ADMIN_EMAIL=<ADMIN_EMAIL>
```

`/diag`, `/diag/export/json` et `/diag/export/markdown` peuvent contenir des informations système : ne jamais les exposer publiquement sans authentification, reverse proxy HTTPS et token applicatif.

Le reverse proxy doit joindre l'application sur `127.0.0.1:8000`. Ne pas publier directement le port FastAPI sur une interface publique.

Exemple préparatoire :

```text
docs/vps/compose.vps.example.yaml
```
