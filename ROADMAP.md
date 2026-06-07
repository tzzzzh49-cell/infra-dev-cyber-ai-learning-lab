# Roadmap

## v0.1.0 - Reproduction locale stable

Objectif : stabiliser la base locale du projet.

Inclus :
- API FastAPI minimale ;
- Docker Compose fonctionnel ;
- Makefile utilisable ;
- documentation initiale ;
- reproduction Fedora 44 validée ;
- première cible Ubuntu 24.04 documentée ;
- règles de sécurité en lecture seule.

## v0.2.0 - Tests, lint et CI

Objectif : rendre le projet vérifiable automatiquement.

Préparé :
- `make check` pour une validation rapide ;
- `make check-full` pour la validation complète ;
- `make shellcheck` pour les scripts Bash ;
- `make compose-config` pour Docker Compose ;
- `make lint-python` pour Ruff ;
- `make lint` pour lancer Ruff, ShellCheck et Docker Compose config ;
- documentation du workflow Git/GitHub.

Prochaines étapes :
- créer une GitHub Action qui lance `make check` sur chaque Pull Request ;
- valider réellement le bootstrap Ubuntu dans une VM Ubuntu 24.04.4 propre ;
- documenter le résultat de cette validation Ubuntu.

## v0.3.0 - Diagnostic réseau avancé

Objectif : enrichir le diagnostic système/réseau.

Prévu :
- collecte interfaces réseau ;
- routes ;
- DNS ;
- ports ouverts ;
- export JSON ;
- export Markdown.

## v0.4.0 - Déploiement VPS

Objectif : déployer le lab sur un VPS sécurisé.

Prévu :
- SSH sécurisé ;
- firewall ;
- Docker Compose distant ;
- HTTPS ;
- nom de domaine ;
- premiers backups.

## v0.5.0 - Résumé IA

Objectif : intégrer progressivement l'API OpenAI.

Prévu :
- résumé de rapports ;
- explication d'erreurs ;
- budget API limité ;
- absence d'exécution automatique de commandes.

## v0.6.0 - OpenClaw contrôlé

Objectif : intégrer OpenClaw avec sécurité.

Prévu :
- allowlist stricte ;
- runbooks ;
- mode lecture seule ;
- sandbox ;
- validation humaine.
