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

Objectif : préparer les livrables définitifs de la semaine 1 sans ajouter de fonctionnalité applicative lourde.

Axes de travail :
- rendre le projet cohérent avec son nom actuel `infra-dev-cyber-ai-learning-lab` ;
- nettoyer les anciens noms lorsqu'ils désignent le projet actuel ;
- sécuriser la configuration locale avec une exposition par défaut sur `127.0.0.1` ;
- ajouter un exemple de configuration VPS sans secret et sans exposition directe de `/diag` ;
- préparer la validation réelle sur Ubuntu 24.04.4 LTS Desktop ;
- préparer la future CI GitHub Actions en gardant `make check` et `make check-full` comme commandes de référence ;
- garder le projet en mode lecture seule.

Limites de la semaine 1 :
- ne pas ajouter GitHub Actions dans cette tâche ;
- ne pas ajouter Caddy, Restic, PostgreSQL, OpenAI API, OpenClaw, Containerlab, déploiement VPS ou authentification ;
- ne pas exposer publiquement `/diag` ;
- ne pas introduire de secrets.

À faire séparément :
- créer la checklist de validation Ubuntu 24.04.4 LTS Desktop dans une tâche dédiée ;
- le fichier `docs/checklists/validation-ubuntu-24.04.4-desktop.md` ne doit pas être créé pour cette tâche.

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
