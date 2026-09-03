# Application FastAPI

Ce dossier contient le service de diagnostic construit par le parcours.

| Emplacement | Rôle |
| --- | --- |
| `main.py` | routes FastAPI et exports |
| `auth.py` | authentification OIDC, RBAC et mode local |
| `diagnostics.py` | collecte système et réseau en lecture seule |
| `logging_config.py` | journalisation applicative |
| `Dockerfile` | image d'exécution non-root |
| `requirements.txt` | dépendances d'exécution |
| `requirements-dev.txt` | dépendances de test et de qualité |
| `tests/` | tests automatisés de l'API et du cockpit |

Commandes utiles depuis la racine :

```bash
make run
make health
make diag
make test
```

L'[architecture](../docs/architecture.md) décrit les flux complets et les
garde-fous de sécurité.
