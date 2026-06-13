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

## v0.2.0 - Cohérence, sécurité locale et préparation Ubuntu/CI

Objectif : livrer une base cohérente, sécurisée localement et validée sur Ubuntu 24.04.4 LTS Desktop.

Inclus :
- rendre le dépôt cohérent avec son nom actuel `infra-dev-cyber-ai-learning-lab` ;
- nettoyer les noms historiques quand ils désignent le projet actuel ;
- sécuriser la configuration locale avec une exposition par défaut sur `127.0.0.1` ;
- ajouter un exemple d'environnement VPS sans secret et sans exposition directe de `/diag` ;
- préparer la validation réelle sur Ubuntu 24.04.4 LTS Desktop ;
- préparer la future CI GitHub Actions sans créer encore de workflow ;
- garder le projet en mode lecture seule, sans commande destructive et sans secret.

Limites de cette étape :
- ne pas ajouter GitHub Actions ;
- ne pas ajouter Caddy, Restic, PostgreSQL, OpenAI API, OpenClaw, Containerlab, déploiement VPS ou authentification ;
- ne pas ajouter de nouvelles grosses fonctionnalités applicatives.

Note : la création de la checklist Ubuntu `docs/checklists/validation-ubuntu-24.04.4-desktop.md` est prévue séparément et ne doit pas être faite dans cette tâche.

Prochaines étapes après semaine 1 :
- valider réellement le bootstrap Ubuntu dans une VM Ubuntu 24.04.4 LTS Desktop propre ;
- documenter le résultat de cette validation Ubuntu dans le livrable dédié ;
- créer ensuite une GitHub Action qui lance `make check` sur chaque Pull Request.

## v0.3.0 - Diagnostic réseau avancé

Objectif : enrichir le diagnostic système/réseau.

Inclus / livré :
- collecte des interfaces réseau ;
- collecte des routes ;
- collecte DNS via `/etc/resolv.conf` et `resolvectl` si disponible ;
- collecte des ports ouverts ;
- collecte disque ;
- collecte mémoire ;
- collecte Docker via `docker ps` en lecture seule ;
- export JSON dans `outputs/reports` ;
- export Markdown dans `outputs/reports` ;
- tests API et diagnostics ;
- documentation dédiée du diagnostic réseau avancé.

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
