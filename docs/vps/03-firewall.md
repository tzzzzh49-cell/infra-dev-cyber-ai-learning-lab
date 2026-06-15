# 03 - Firewall

Objectif : préparer les règles d'exposition d'un futur VPS sans appliquer de changement système dans cette tâche.

## Politique attendue

- SSH reste limité aux administrateurs prévus.
- HTTP et HTTPS sont ouverts uniquement pour Caddy.
- L'API FastAPI ne doit pas être exposée directement sur une interface publique.
- Le port applicatif reste lié à `127.0.0.1`.
- `/diag`, `/diag/export/json` et `/diag/export/markdown` restent protégés par authentification reverse proxy et `DIAG_ACCESS_TOKEN`.

## Ports à documenter hors dépôt

| Usage | Port | Exposition attendue |
|---|---:|---|
| SSH | 22 ou port choisi hors dépôt | Administration uniquement |
| HTTP | 80 | Redirection ou challenge ACME via Caddy |
| HTTPS | 443 | Entrée publique Caddy |
| FastAPI | 8000 | Localhost uniquement |

## Points de contrôle

- Valider l'accès SSH non-root avant tout changement.
- Conserver une session de secours pendant la modification réelle du firewall.
- Vérifier que l'API répond via Caddy et non directement depuis Internet.
- Refuser tout accès diagnostic non authentifié.

Ce document ne contient volontairement aucune commande firewall prête à copier. Les commandes réelles dépendent du fournisseur VPS, de l'image serveur et de la procédure de secours validée.
