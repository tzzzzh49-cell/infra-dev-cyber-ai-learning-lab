# Préparation v0.4.0 VPS

Cette section prépare la future étape v0.4.0 de déploiement VPS. Elle ne constitue pas un déploiement réel.

Principes :

- aucune adresse IP réelle ;
- aucun domaine réel obligatoire ;
- aucun secret ;
- exposition applicative locale privilégiée sur `127.0.0.1` ;
- reverse proxy HTTPS devant l'application avant toute exposition publique ;
- `/diag` et les exports de diagnostic ne doivent jamais être publics sans authentification ;
- `/diag` est protégé par défaut par un token dont seul le hash est côté application ;
- `DIAG_ACCESS_TOKEN_HASH` doit venir d'un gestionnaire de secrets ou d'un fichier monté hors dépôt ;
- toute action système réelle doit être relue et validée manuellement hors dépôt.

Documents :

1. [Première connexion](01-premiere-connexion.md)
2. [Sécurisation SSH](02-securisation-ssh.md)
3. [Firewall](03-firewall.md)
4. [Installation Docker](04-install-docker.md)
5. [Déploiement Compose](05-deploiement-compose.md)
6. [HTTPS et reverse proxy](06-https-reverse-proxy.md)
7. [DNS et Cloudflare](07-dns-cloudflare.md)

Exemples de configuration :

- [Caddyfile.example](Caddyfile.example)
- [nginx.reverse-proxy.example.conf](nginx.reverse-proxy.example.conf)
- [compose.vps.example.yaml](compose.vps.example.yaml)

Variables préparatoires :

- `.env.vps.example` documente les variables attendues sans secret réel ;
- le fichier privé réel doit rester hors Git ;
- `DIAG_ACCESS_TOKEN_HASH` doit être défini hors dépôt avant toute exposition de `/diag` ;
- le proxy peut utiliser un secret runtime distinct `DIAG_UPSTREAM_TOKEN` pour injecter `X-Diag-Token` après authentification basique ou OAuth.
