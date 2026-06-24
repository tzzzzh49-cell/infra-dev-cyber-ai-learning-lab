# 08 - Authentification OAuth2/OIDC

Le profil Compose `public-proxy` utilise OAuth2 Proxy comme client OIDC
confidentiel. Il applique le flux Authorization Code avec PKCE S256 puis transmet
un ID token au service API. L'API revalide ce JWT avant chaque action sensible.

## Contrat avec le fournisseur d'identité

Créer une application Web avec les paramètres suivants :

- grant : Authorization Code uniquement, avec PKCE S256 ;
- redirect URI exacte : `https://<LAB_DOMAIN>/oauth2/callback` ;
- durée maximale du JWT : 15 minutes ;
- signature asymétrique RS256/384/512, PS256/384/512 ou ES256/384/512 ;
- clé RSA d'au moins 2048 bits ou clé EC d'au moins 256 bits ;
- issuer et JWKS servis en HTTPS ;
- audience dédiée à cette API ;
- claim de rôles contenant uniquement `user`, `partner` ou `admin` ;
- claim `amr` contenant `mfa`, ou claim `acr` accepté, pour les admins.

Ne pas activer les flows Implicit, Resource Owner Password ou les algorithmes
symétriques pour cette application. Aucun identifiant utilisateur ne doit être
transmis dans une URL ou géré directement par Nginx/FastAPI.

## Variables non secrètes

```text
OIDC_ISSUER_URL=https://<IDP>/...
OIDC_JWKS_URL=https://<IDP>/.../jwks
OIDC_CLIENT_ID=<CLIENT_ID>
OIDC_AUDIENCE=<AUDIENCE>
OIDC_REDIRECT_URL=https://<LAB_DOMAIN>/oauth2/callback
OIDC_ROLES_CLAIM=roles
OIDC_ACR_VALUES=<ACR_DEMANDE_A_L_IDP>
OIDC_MFA_ACR_VALUES=<ACR_ACCEPTES_PAR_L_API>
```

`OIDC_AUDIENCE` correspond généralement au client ID ou à l'audience API
déclarée par l'IdP. Les valeurs exactes dépendent du fournisseur.

## Secrets runtime

Le secret client et la clé de chiffrement des cookies sont lus depuis des
fichiers montés en lecture seule :

```text
OIDC_CLIENT_SECRET_FILE=<CHEMIN_PRIVE_HORS_GIT>
OIDC_COOKIE_SECRET_FILE=<CHEMIN_PRIVE_HORS_GIT>
```

Ces fichiers doivent appartenir à `root:10001`, avoir le mode `0440` et ne
jamais être ajoutés au dépôt. La clé de cookie doit contenir une
valeur aléatoire compatible OAuth2 Proxy de 16, 24 ou 32 octets.

## RBAC appliqué par l'API

| Action | user | partner | admin |
|---|---:|---:|---:|
| Endpoints publics | oui | oui | oui |
| `GET /diag` | non | oui | oui + MFA |
| Exports JSON/Markdown | non | non | oui + MFA |

Tout rôle absent ou inconnu est refusé. La gateway ne décide jamais seule de
l'autorisation.

## Bruteforce, credential stuffing et MFA

Le dépôt ne reçoit aucun mot de passe. Configurer dans l'IdP : MFA obligatoire
pour les admins, limitation par compte/IP, verrouillage progressif, détection de
mots de passe compromis et CAPTCHA adaptatif après plusieurs échecs. L'API
bloque en complément une IP pendant cinq minutes après cinq JWT invalides.

## Activation

Après configuration de l'IdP et des fichiers secrets :

```bash
make public-config
sudo env MTLS_DIR=/etc/infra-lab/mtls make public-up
PUBLIC_URL='https://<LAB_DOMAIN>' make public-health
```

Le démarrage réel modifie l'état des services : le relire et le confirmer avant
exécution. `public-up` refuse de démarrer si le jeu mTLS complet n'est pas
valide. Sans configuration OIDC complète, les routes sensibles refusent l'accès.
