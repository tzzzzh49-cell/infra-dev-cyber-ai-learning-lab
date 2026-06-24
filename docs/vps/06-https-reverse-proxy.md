# 05 - HTTPS et reverse proxy

Objectif : exposer l'API derrière Nginx, ModSecurity, OWASP CRS et OAuth2 Proxy.

Principes :

- terminer TLS via un reverse proxy maintenu ;
- conserver le port API publié uniquement sur `127.0.0.1:8000` ;
- imposer mTLS entre Nginx et FastAPI ;
- placer OAuth2 Proxy devant `/diag` et `/diag/*` avec Authorization Code et PKCE S256 ;
- transmettre au backend un JWT OIDC dans `Authorization: Bearer`, puis le
  revalider et l'autoriser dans l'API ;
- ne pas documenter de domaine réel obligatoire ;
- ne pas committer de certificat, clé privée ou token DNS.

Fichiers actifs :

```text
compose.public.yaml
nginx/default.conf.template
nginx/api_proxy.conf
nginx/oauth2_proxy.conf
```

Placeholders à remplacer hors dépôt :

- `<LAB_DOMAIN>` : domaine de lab, jamais un domaine réel dans l'exemple commité ;
- `<ADMIN_EMAIL>` : email utilisé pour ACME ;
- `OIDC_ISSUER_URL`, `OIDC_JWKS_URL`, `OIDC_CLIENT_ID` et `OIDC_AUDIENCE` ;
- `OIDC_CLIENT_SECRET_FILE` et `OIDC_COOKIE_SECRET_FILE`, montés hors Git.

Points de contrôle avant exposition :

- le binding API Compose reste forcé sur `127.0.0.1` ;
- `APP_ENV=vps` est actif côté application ;
- `DIAG_PROTECTION_DISABLED=false` ;
- Nginx interroge OAuth2 Proxy avant chaque requête `/diag*` ;
- Nginx retire les en-têtes d'identité clients avant de définir
  `X-Verified-Client-IP` ;
- les quotas Nginx renvoient 429, avec un quota `/diag` plus strict ;
- ModSecurity et OWASP CRS sont actifs au niveau de paranoïa 1 ;
- Swagger, ReDoc et OpenAPI sont désactivés en mode VPS ;
- l'API valide issuer, audience, signature, expiration, durée et rôles du JWT ;
- aucun domaine, token DNS, certificat ou mot de passe réel n'est commité.
- les routes publiques non sensibles ne transmettent pas de token inutilement.

Tout exemple doit utiliser des placeholders comme `<LAB_DOMAIN>` et `<ADMIN_EMAIL>`.

Le provisionnement hôte est dans `scripts/provision_public_proxy.sh`. Il génère
l'autorité mTLS interne, installe l'unité systemd non-root et applique UFW après
confirmation. Il ne génère pas le certificat public : obtenir celui de
`<LAB_DOMAIN>` avec `<ADMIN_EMAIL>` hors dépôt.

La configuration OIDC complète est décrite dans
[`08-authentification-oidc.md`](08-authentification-oidc.md). Le secret client et
la clé de cookie restent dans des fichiers privés montés au runtime.
