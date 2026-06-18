# AGENTS.md — secure_ai_ops_lab

## Mission

Ce dépôt est un laboratoire d’apprentissage Secure AI Ops.

Objectif :
comprendre, construire et documenter progressivement.

Priorités :
simplicité, lisibilité, sécurité, traçabilité, vérification.

## Principes par défaut

- Utiliser Ponytail en mode `full` sauf demande explicite contraire.
- Proposer la solution minimale qui fonctionne.
- Préférer Python standard library, Bash simple, Docker Compose simple et fichiers de configuration lisibles.
- Ne pas ajouter de dépendance, de service, de base de données, d’API, de cache, de queue, de scheduler ou d’abstraction interne sans besoin démontré dans le dépôt.
- Garder les changements petits, séparés et faciles à relire.
- Préférer un script clair à un framework interne, une classe abstraite, un wrapper ou une orchestration inutile.

## Sécurité non négociable

- Ne jamais exécuter d’action destructive, irréversible ou à impact système sans validation humaine explicite.
- Cela inclut notamment : `sudo`, suppression de fichiers, suppression d’images ou volumes Docker, `git push`, rotation de clés, accès distant, modification VPS, arrêt ou redémarrage de services, suppression d’environnements ou de données.
- Ne jamais afficher, logger ou commiter de secrets.
- Utiliser `.env.example` pour documenter les variables, jamais de vraies valeurs.
- Valider les entrées aux frontières : fichiers, variables d’environnement, arguments CLI, requêtes réseau.
- Préserver des logs utiles et des erreurs explicites.
- Pour toute action sensible, préférer des commandes directes et simples. Éviter les chaînes shell complexes qui masquent plusieurs actions dans une seule commande.

## Ce qu’il faut éviter

- Ne pas créer de microservice si un script suffit.
- Ne pas créer de module `utils` générique sans usage immédiat.
- Ne pas ajouter de dépendance “au cas où”.
- Ne pas remplacer une commande Linux claire par du code Python inutile.
- Ne pas faire de refactoring non demandé.
- Ne pas masquer une action système dangereuse derrière une fonction “safe” sans garde-fous réels.

## Méthode de travail

### Avant de modifier

1. Lire les fichiers pertinents.
2. Résumer le problème en termes simples.
3. Proposer le plus petit changement possible.
4. Expliquer pourquoi une solution plus simple ne suffit pas.
5. Si la demande impose “ne modifie rien” ou “attends validation”, s’arrêter après l’analyse.

### Pendant la modification

1. Modifier uniquement les fichiers nécessaires.
2. Garder des noms explicites.
3. Éviter les refactorings non demandés.
4. Ajouter ou adapter les tests seulement si cela sert une vérification réelle.
5. Ne pas élargir le périmètre sans raison explicite.

### Après la modification

1. Montrer le diff ou en faire un résumé fidèle.
2. Expliquer exactement ce qui a changé.
3. Donner les commandes de vérification.
4. Signaler les limites restantes, hypothèses et risques résiduels.

## Définition de terminé

Une tâche est terminée seulement si :
- le changement est minimal et cohérent avec la demande ;
- les fichiers touchés sont justifiés ;
- les vérifications pertinentes ont été proposées ou exécutées selon le contexte ;
- aucun secret n’a été exposé ;
- les limites restantes sont explicites.

## Vérification

Utiliser d’abord les commandes déjà prévues par le dépôt. Ne pas inventer de pipeline complexe.

Exemples selon les fichiers présents :
- `python -m pytest`
- `python -m compileall .`
- `shellcheck scripts/*.sh`
- `docker compose config`
- `git diff --check`

## Si le contexte manque

- Ne pas inventer.
- Dire ce qui manque.
- Indiquer quel fichier ou quelle commande de lecture permettrait de lever le doute.
