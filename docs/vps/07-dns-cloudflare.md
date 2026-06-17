# 07 - DNS et Cloudflare

Objectif : préparer la configuration DNS d'un futur VPS sans domaine réel, sans IP réelle et sans token Cloudflare.

## Placeholders

Utiliser uniquement des placeholders dans le dépôt :

- `<LAB_DOMAIN>` pour le domaine public ;
- `<VPS_PUBLIC_IP>` pour l'adresse IPv4 du VPS ;
- `<VPS_PUBLIC_IPV6>` pour l'adresse IPv6 si utilisée ;
- `<ADMIN_EMAIL>` pour l'email ACME ;
- `<CLOUDFLARE_ACCOUNT>` pour une note de compte sans identifiant sensible.

## Enregistrements DNS attendus

| Type | Nom | Valeur | Remarque |
|---|---|---|---|
| A | `<LAB_DOMAIN>` | `<VPS_PUBLIC_IP>` | Placeholder uniquement |
| AAAA | `<LAB_DOMAIN>` | `<VPS_PUBLIC_IPV6>` | Optionnel |

## Stratégie Cloudflare

- Commencer en mode DNS uniquement pendant la validation TLS Caddy, sauf choix explicite documenté.
- Ne pas commiter de token API Cloudflare.
- Ne pas commiter de domaine réel.
- Ne pas commiter d'adresse IP réelle.
- Utiliser le mode proxy Cloudflare seulement après vérification de la chaîne HTTPS et des en-têtes côté Caddy.

## Règles d'exposition

- L'API FastAPI reste liée à `127.0.0.1:8000`.
- Le trafic public arrive uniquement sur Caddy en HTTPS.
- `/health` peut rester accessible pour contrôle léger.
- `/diag`, `/diag/export/json` et `/diag/export/markdown` doivent rester protégés par authentification reverse proxy et par token applicatif hashé ou privé.

## Points à valider hors dépôt

- Résolution DNS de `<LAB_DOMAIN>` vers le VPS.
- Certificat TLS obtenu par Caddy.
- Redirection ou refus des accès HTTP non sécurisés selon la configuration choisie.
- Accès refusé aux diagnostics sans authentification.
- Accès autorisé aux diagnostics uniquement après authentification.
