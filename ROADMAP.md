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

## v0.2.0 - Semaine 1 : cohérence, sécurité locale et préparation CI

Objectif : préparer des livrables de base propres avant d'ajouter de nouvelles briques.

La semaine 1 vise à :
- rendre le projet cohérent avec son nom actuel `infra-dev-cyber-ai-learning-lab` ;
- nettoyer les anciens noms lorsqu'ils désignent le projet courant ;
- sécuriser la configuration locale avec une exposition par défaut sur `127.0.0.1` ;
- ajouter un exemple d'environnement VPS sans secret et sans exposition publique directe ;
- préparer la validation réelle Ubuntu 24.04.4 LTS Desktop ;
- préparer la future CI GitHub Actions sans encore créer de workflow ;
- garder le projet en mode lecture seule, sans commande destructive et sans secret.

Préparé :
- `make check` pour une validation rapide ;
- `make check-full` pour la validation complète ;
- `make shellcheck` pour les scripts Bash ;
- `make compose-config` pour Docker Compose ;
- `make lint-python` pour Ruff ;
- `make lint` pour lancer Ruff, ShellCheck et Docker Compose config ;
- documentation du workflow Git/GitHub ;
- configuration locale sûre par défaut ;
- documentation README alignée avec le dépôt canonique.

À faire séparément :
- créer la checklist de validation Ubuntu 24.04.4 LTS Desktop dans une tâche dédiée ;
- valider réellement le bootstrap Ubuntu dans une VM Ubuntu 24.04.4 propre ;
- documenter le résultat de cette validation Ubuntu ;
- créer plus tard une GitHub Action qui lance `make check` sur chaque Pull Request.

La création de `docs/checklists/validation-ubuntu-24.04.4-desktop.md` est explicitement prévue séparément et ne doit pas être faite dans cette tâche.

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
