# Espace de progression

Ce dossier relie le guide officiel, le lab technique et les preuves produites
par l'apprenant.

Le dépôt étant public, tout contenu ajouté ici doit être publiable. Les preuves
brutes chiffrées, secrets et identifiants réels restent dans les stockages
locaux prévus par le cockpit, jamais dans Git.

| Emplacement | Rôle | Modification manuelle |
| --- | --- | --- |
| `roadmap.md` | vue d'ensemble générée du guide actif | non ; utiliser `make learn-roadmap` |
| `lab-map.yml` | correspondance entre livrables et composants existants | maintenance ponctuelle |
| `days/<JOUR>/learner.md` | travail personnel de la journée active | oui, par l'apprenant |
| `days/<JOUR>/.proof/` | métadonnées et revue de preuve | non, sauf procédure prévue |
| `templates/` | modèle d'une nouvelle journée | maintenance du cockpit |
| `schemas/` | contrats JSON des preuves | maintenance du cockpit |
| `local.example.json` | exemple de configuration locale | copier hors Git, ne pas personnaliser ici |

## Parcours normal

Depuis la racine :

```bash
make learn
```

Le cockpit choisit la journée, ouvre la bonne rubrique et masque la mécanique
inutile. Le [tutoriel](../TUTORIEL.md) explique le premier lancement ; la
[carte du dépôt](../docs/repository-map.md) situe cet espace dans l'ensemble du
projet.

Le guide lui-même reste dans [`../curriculum/`](../curriculum/README.md).
