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

## v0.2.0 - Cohérence, sécurité locale et préparation CI

Objectif semaine 1 : consolider les livrables de base avant d'ajouter de nouvelles fonctionnalités.

Cette étape vise à :

- rendre le projet cohérent avec son nom actuel `infra-dev-cyber-ai-learning-lab` ;
- sécuriser la configuration locale avec une exposition par défaut sur `127.0.0.1` ;
- préparer la validation réelle sur Ubuntu 24.04.4 LTS Desktop ;
- préparer la future CI GitHub Actions sans créer encore de workflow ;
- garder le projet en mode lecture seule, sans commandes destructives, secrets ou exposition publique non protégée de `/diag`.

Préparé :
- `make check` pour une validation rapide ;
- `make check-full` pour la validation complète ;
- `make shellcheck` pour les scripts Bash ;
- `make compose-config` pour Docker Compose ;
- `make lint-python` pour Ruff ;
- `make lint` pour lancer Ruff, ShellCheck et Docker Compose config ;
- documentation du workflow Git/GitHub ;
- exemples d'environnement local et VPS sûrs par défaut.

À faire séparément :
- créer la checklist de validation Ubuntu 24.04.4 LTS Desktop dans une tâche dédiée ;
- valider réellement le bootstrap Ubuntu dans une VM Ubuntu 24.04.4 propre ;
- documenter le résultat de cette validation Ubuntu ;
- créer une GitHub Action qui lance `make check` sur chaque Pull Request.

> La checklist Ubuntu `docs/checklists/validation-ubuntu-24.04.4-desktop.md` est prévue séparément et ne doit pas être créée dans la tâche semaine 1 actuelle.

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
