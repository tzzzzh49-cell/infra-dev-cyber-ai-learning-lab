# 03 - Firewall

Objectif : préparer les règles d'exposition d'un futur VPS sans appliquer de changement système dans cette tâche.

## Politique attendue

- SSH reste limité aux administrateurs prévus.
- HTTP et HTTPS sont ouverts uniquement pour Nginx.
- L'API FastAPI ne doit pas être exposée directement sur une interface publique.
- Le port applicatif reste lié à `127.0.0.1`.
- `/diag`, `/diag/export/json` et `/diag/export/markdown` restent protégés par OAuth2/OIDC côté reverse proxy et par RBAC côté API.

## Ports à documenter hors dépôt

| Usage | Port | Exposition attendue |
|---|---:|---|
| SSH | 22 ou port choisi hors dépôt | Administration uniquement |
| HTTP | 80 | Redirection 301 vers HTTPS via Nginx |
| HTTPS | 443 | Entrée publique Nginx |
| FastAPI | 8000 | Localhost uniquement |

## Points de contrôle

- Valider l'accès SSH non-root avant tout changement.
- Conserver une session de secours pendant la modification réelle du firewall.
- Vérifier que l'API répond via Nginx et non directement depuis Internet.
- Refuser tout accès diagnostic non authentifié.

Le script `scripts/provision_public_proxy.sh` applique cette politique UFW
uniquement après `APPLY_CONFIRM=yes`. Il faut garder une session SSH de secours
pendant son exécution.
