# Préparation v0.4.0 VPS

Cette section prépare la future étape v0.4.0 de déploiement VPS. Elle ne constitue pas un déploiement réel.

Principes :

- aucune adresse IP réelle ;
- aucun domaine réel obligatoire ;
- aucun secret ;
- exposition applicative locale privilégiée sur `127.0.0.1` ;
- reverse proxy HTTPS devant l'application avant toute exposition publique ;
- `/diag` et les exports de diagnostic ne doivent jamais être publics sans authentification ;
- `/diag` est protégé par OAuth2/OIDC et un RBAC vérifié dans l'API ;
- les secrets OIDC sont montés depuis des fichiers privés hors dépôt ;
- toute action système réelle doit être relue et validée manuellement hors dépôt.

Documents :

1. [Première connexion](01-premiere-connexion.md)
2. [Sécurisation SSH](02-securisation-ssh.md)
3. [Firewall](03-firewall.md)
4. [Installation Docker](04-install-docker.md)
5. [Déploiement Compose](05-deploiement-compose.md)
6. [HTTPS et reverse proxy](06-https-reverse-proxy.md)
7. [DNS et Cloudflare](07-dns-cloudflare.md)
8. [Authentification OAuth2/OIDC](08-authentification-oidc.md)
9. [Migration vers un nouveau VPS](09-migration-nouveau-vps.md)

Exemples de configuration :

- [nginx.reverse-proxy.example.conf](nginx.reverse-proxy.example.conf)
- [compose.vps.example.yaml](compose.vps.example.yaml)
- [`compose.public.yaml`](../../compose.public.yaml) pour le proxy public réel ;
- [`nginx/default.conf.template`](../../nginx/default.conf.template) pour le routage.

Variables préparatoires :

- `.env.vps.example` documente les variables attendues sans secret réel ;
- le fichier privé réel doit rester hors Git ;
- l'issuer, le JWKS, l'audience, le client et les claims de rôles doivent être
  configurés avant toute exposition ;
- le secret client et la clé de cookie restent dans des fichiers runtime.
