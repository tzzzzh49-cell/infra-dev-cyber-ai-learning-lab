# 05 - HTTPS et reverse proxy

Objectif : préparer l'exposition HTTPS future avec Caddy, sans imposer de déploiement réel dans cette étape.

Principes :

- terminer TLS via un reverse proxy maintenu ;
- proxy vers `127.0.0.1:8000` uniquement ;
- ajouter une authentification avant tout accès public à `/diag` et aux exports ;
- transmettre au backend un `X-Diag-Token` issu d'une variable d'environnement privée ;
- ne pas documenter de domaine réel obligatoire ;
- ne pas committer de certificat, clé privée ou token DNS.

Fichier exemple :

```text
docs/vps/Caddyfile.example
```

Placeholders à remplacer hors dépôt :

- `<LAB_DOMAIN>` : domaine de lab, jamais un domaine réel dans l'exemple commité ;
- `<ADMIN_EMAIL>` : email utilisé pour ACME ;
- `<BASIC_AUTH_USER>` : utilisateur de l'authentification reverse proxy ;
- `<CADDY_HASHED_PASSWORD>` : hash Caddy généré hors dépôt ;
- `DIAG_ACCESS_TOKEN` : variable d'environnement privée partagée avec l'application.

Points de contrôle avant exposition :

- `APP_HOST=127.0.0.1` reste actif côté Compose ;
- `APP_ENV=vps` est actif côté application ;
- `DIAG_ACCESS_TOKEN` est défini hors Git ;
- Caddy applique une authentification sur les routes de diagnostic ;
- aucun domaine, token DNS, certificat ou mot de passe réel n'est commité.

Tout exemple doit utiliser des placeholders comme `<LAB_DOMAIN>` et `<ADMIN_EMAIL>`.
