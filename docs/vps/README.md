# Préparation v0.4.0 VPS

Cette section prépare la future étape v0.4.0 de déploiement VPS. Elle ne constitue pas un déploiement réel.

Principes :

- aucune adresse IP réelle ;
- aucun domaine réel obligatoire ;
- aucun secret ;
- exposition applicative locale privilégiée sur `127.0.0.1` ;
- reverse proxy HTTPS devant l'application avant toute exposition publique ;
- `/diag` et les exports de diagnostic ne doivent jamais être publics sans authentification ;
- `APP_ENV=vps` doit activer la protection applicative par `DIAG_ACCESS_TOKEN`.

Documents :

1. [Première connexion](01-premiere-connexion.md)
2. [Sécurisation SSH](02-securisation-ssh.md)
3. [Installation Docker](03-install-docker.md)
4. [Déploiement Compose](04-deploiement-compose.md)
5. [HTTPS et reverse proxy](05-https-reverse-proxy.md)
6. [DNS et Cloudflare](06-dns-cloudflare.md)

Exemple de configuration Caddy :

- [Caddyfile.example](Caddyfile.example)
