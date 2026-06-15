# Modèle de sécurité OpenClaw

Statut : documentation préparatoire, non active.

OpenClaw ne doit pas être activé par défaut dans ce projet. Les fichiers de ce dossier décrivent seulement le cadre attendu pour une future intégration contrôlée.

## Principes

- Refus par défaut.
- Lecture seule par défaut.
- Allowlist explicite et limitée.
- Validation humaine avant toute action.
- Aucun secret dans le dépôt.
- Aucune commande shell libre.
- Journalisation des décisions futures.

## Actions interdites

Interdictions explicites :

- `sudo` et élévation de privilèges ;
- `rm`, suppressions et nettoyages destructifs ;
- `docker stop`, `docker rm`, `docker system prune` et arrêts de services ;
- `ip route add`, `ip route del`, changements d'interface et modifications réseau ;
- modifications firewall ;
- changements DNS réels ;
- actions cloud, Terraform, Kubernetes ou Ansible de modification ;
- exécution automatique sans validation humaine.

## Actions envisageables plus tard

Uniquement après revue :

- lire un rapport déjà généré ;
- proposer une commande read-only issue d'une allowlist ;
- demander validation humaine ;
- produire un résumé ou une checklist.

## Conditions avant activation future

- tests dédiés ;
- journalisation ;
- configuration explicite ;
- documentation des risques ;
- procédure de désactivation ;
- revue humaine avant toute commande proposée.
