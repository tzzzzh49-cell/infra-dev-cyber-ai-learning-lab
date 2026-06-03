# Note de migration legacy

Le dépôt contenait avant cette évolution un lab réseau/FastAPI.
Les dossiers et fichiers historiques sont conservés pour éviter une suppression brutale :

- `app/` ;
- `ansible/` ;
- `compose.yaml` ;
- `Makefile` ;
- anciens scripts de bootstrap et diagnostic ;
- documents de reproductibilité et sécurité historiques ;
- `openclaw/allowlists/` et anciens runbooks.

## Stratégie prudente

- Ne pas supprimer ces fichiers tant qu'une décision de migration n'est pas prise.
- Les déplacer plus tard vers `docs/legacy/` ou un sous-projet si nécessaire.
- Conserver les éléments utiles : reproductibilité Ubuntu, workflow Git, principes de sécurité.
- Éviter de mélanger les anciennes commandes FastAPI avec le MVP Hermes + OpenClaw.

## TODO

- Inventorier ce qui reste utile pour le portfolio.
- Décider si le lab FastAPI devient une annexe.
- Supprimer ou déplacer uniquement via une Pull Request dédiée.
