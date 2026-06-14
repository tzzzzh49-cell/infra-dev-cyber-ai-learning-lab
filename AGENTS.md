# Instructions pour agents IA

## Contexte du projet

`infra-dev-cyber-ai-learning-lab` est un laboratoire local d'apprentissage DevOps, Linux, Docker, FastAPI, diagnostic défensif et bonnes pratiques DevSecOps. Le projet doit rester reproductible, auditable et sûr par défaut.

La cible prioritaire est **Ubuntu 26.04 LTS Server**. Fedora Workstation 44 reste une cible secondaire. Ubuntu 24.04.4 LTS Desktop est conservée comme cible historique validée.

## Règles de sécurité absolues

- Conserver le mode **lecture seule** pour les diagnostics.
- Ne jamais ajouter de commande destructive ou modifiant le système hôte.
- Ne jamais ajouter de secret réel, token, clé privée, mot de passe, adresse IP sensible ou domaine privé.
- Ne pas exposer publiquement `/diag` sans authentification et reverse proxy sécurisé.
- Privilégier `127.0.0.1` pour l'exposition locale de l'API.
- Ne pas intégrer OpenAI API dans les tâches qui ne le demandent pas explicitement.
- Ne pas intégrer OpenClaw dans les tâches qui ne le demandent pas explicitement.
- Ne jamais ajouter de logique d'exécution automatique de commandes par IA.

## Commandes autorisées

Les agents peuvent utiliser les commandes de validation et de lecture suivantes :

- `git status`, `git diff`, `git log`, `git branch`, `git switch -c <branche>` ;
- `make check` ;
- `make test` ;
- `make lint` ;
- `make compose-config` ;
- `make lint-python` ;
- `make shellcheck` ;
- `python -m pytest app/tests -v` ;
- `docker compose config` via `./scripts/compose.sh config` ;
- commandes de consultation non destructives comme `cat`, `sed`, `find`, `rg`.

`make check-full` est recommandé avant merge, mais il peut être plus lourd car il inclut des vérifications complémentaires comme le build Docker et Ansible.

## Commandes interdites

Ne pas utiliser de commandes destructives ou risquées, notamment :

- suppression massive : `rm -rf`, `find ... -delete` ;
- modification système : `sudo`, `apt remove`, `dnf remove`, `systemctl enable/disable` ;
- manipulation disque : `mkfs`, `dd`, `mount` hors contexte explicitement validé ;
- exposition réseau publique non protégée ;
- commandes téléchargeant ou exécutant du code distant sans revue.

## Workflow de modification

1. Ne pas modifier directement `master` : créer une branche dédiée.
2. Lire les instructions locales avant modification.
3. Faire des changements petits, cohérents et documentés.
4. Préserver la compatibilité Docker Compose et les chemins existants.
5. Isoler les tests avec `tmp_path`/`monkeypatch` lorsqu'ils écrivent des fichiers.
6. Vérifier qu'aucun secret ou donnée réelle sensible n'est ajouté.
7. Exécuter les validations obligatoires avant PR.

## Validations obligatoires avant Pull Request

À exécuter avant de proposer une PR :

```bash
make check
make test
make lint
make compose-config
```

Si possible avant merge :

```bash
make check-full
```

Si `make check-full` n'est pas exécuté, expliquer pourquoi dans la PR.

## Format des commits

Utiliser des messages courts, explicites et orientés changement, par exemple :

- `Add minimal GitHub Actions CI`
- `Harden FastAPI diagnostics tests`
- `Document VPS preparation workflow`

## Limites OpenAI API et OpenClaw

- Aucune intégration OpenAI API ne doit être ajoutée sans tâche dédiée.
- Aucune intégration OpenClaw ne doit être ajoutée sans tâche dédiée.
- Les futures intégrations devront rester en lecture seule par défaut, sans exécution automatique de commandes et avec validation humaine.
