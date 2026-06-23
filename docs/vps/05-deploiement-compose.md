# 04 - Déploiement Docker Compose

Objectif : préparer le futur lancement Compose sans l'effectuer dans cette tâche.

Recommandations :

- cloner le dépôt sur le VPS avec une branche/tag validé ;
- conserver le binding Compose forcé sur `127.0.0.1` ;
- définir `APP_ENV=vps` dans un fichier `.env` privé ;
- configurer l'issuer, le JWKS, l'audience et le client OIDC ;
- monter le secret client et la clé de cookie depuis des fichiers privés hors Git ;
- monter uniquement `outputs/reports/` et `outputs/logs/` ;
- vérifier `make compose-config` avant démarrage ;
- lancer l'application seulement après revue de la configuration.
- utiliser `docs/vps/compose.vps.example.yaml` comme exemple de structure, pas comme configuration finale non relue.

Configuration attendue côté application :

```dotenv
APP_ENV=vps
APP_PORT=8000
DIAG_PROTECTION_DISABLED=false
DIAG_COMMAND_TIMEOUT=3
DIAG_COMMAND_RETRIES=0
OIDC_ISSUER_URL=https://<IDP>/...
OIDC_JWKS_URL=https://<IDP>/.../jwks
OIDC_CLIENT_ID=<CLIENT_ID>
OIDC_AUDIENCE=<AUDIENCE>
OIDC_CLIENT_SECRET_FILE=<CHEMIN_PRIVE>
OIDC_COOKIE_SECRET_FILE=<CHEMIN_PRIVE>
LAB_DOMAIN=<LAB_DOMAIN>
ADMIN_EMAIL=<ADMIN_EMAIL>
```

Le profil Compose `future-persistence` prépare un service Postgres inactif par
défaut. Ne pas l'activer en production sans migrations relues, mot de passe réel
hors Git et sauvegardes validées.

`/diag`, `/diag/export/json` et `/diag/export/markdown` peuvent contenir des
informations système : ne jamais les exposer sans HTTPS, OIDC, MFA admin et RBAC
applicatif.

Le port FastAPI reste publié uniquement sur `127.0.0.1:8000` pour les contrôles
locaux. Dans `compose.public.yaml`, Nginx joint directement le service `api` en
mTLS sur le réseau Compose ; aucune interface publique n'expose le port 8000.

Exemple préparatoire :

```text
docs/vps/compose.vps.example.yaml
```
