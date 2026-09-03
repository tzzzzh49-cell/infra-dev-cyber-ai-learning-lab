# Outils internes du parcours

Ce dossier contient la mécanique du cockpit et de la publication des preuves.
Il ne constitue pas un point d'entrée quotidien pour l'apprenant.

| Fichier | Rôle |
| --- | --- |
| `learn.py` | démarrage, reprise, validation et génération de la roadmap |
| `learning_public_anchor.py` | vérification de l'ancrage GitHub public |
| `learning_publish.py` | production contrôlée du paquet de preuve publique |

Utiliser les façades du `Makefile` depuis la racine :

```bash
make learn
make learn-check
make learn-roadmap
```

Toute modification de ces fichiers doit rester synchronisée avec leurs tests
dans `app/tests/` et, pour la publication, avec les empreintes vérifiées par
`.github/workflows/publish-learning.yml`.
