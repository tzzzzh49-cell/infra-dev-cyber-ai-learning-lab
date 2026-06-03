# Runbook Hermes + OpenClaw Gateway

## Architecture exploitée

Le flux nominal est : utilisateur Telegram ou WhatsApp, OpenClaw Gateway locale, MCP local, Hermes Agent, fournisseur IA configuré, puis réponse via OpenClaw.
Telegram est prioritaire pour le MVP.
WhatsApp arrive plus tard.

## Commandes de statut rapide

```bash
git status --short
scripts/healthcheck.sh
systemctl --user status hermes-openclaw-loop.service
```

Résultat attendu : dépôt propre, healthcheck OK, service actif.

## Vérification systemd

```bash
systemctl --user is-enabled hermes-openclaw-loop.service
systemctl --user is-active hermes-openclaw-loop.service
systemctl --user status hermes-openclaw-loop.service
```

Résultat attendu : `enabled`, `active` et un statut sans crash répété.
Le nom sans `.service` peut fonctionner avec `systemctl`, mais le nom complet reste la référence.

## Logs journalctl

```bash
journalctl --user -u hermes-openclaw-loop.service -n 100 --no-pager
journalctl --user -u hermes-openclaw-loop.service -f
```

Résultat attendu : logs techniques uniquement.
Aucun message privé ne doit apparaître.

## Diagnostic OpenClaw

```bash
command -v openclaw
openclaw --version
openclaw gateway status
```

Résultat attendu : la commande existe et le statut gateway est lisible.
Si `openclaw gateway status` n'existe pas, utilisez l'équivalent de la version officielle.

## Diagnostic Hermes

```bash
command -v hermes
hermes --version
```

Résultat attendu : Hermes est installé et répond.
Ne lancez pas de test LLM fragile basé sur une réponse exacte comme `pong`.

## Diagnostic MCP

À vérifier manuellement selon la version :

```bash
# Exemple générique : remplacer par la commande MCP officielle disponible.
hermes mcp list
```

Résultat attendu : les outils OpenClaw autorisés apparaissent.
Les outils doivent rester limités au strict nécessaire.

## Diagnostic Docker et Compose

Docker Compose est optionnel pour le MVP.
Si utilisé plus tard :

```bash
docker --version
docker compose version
docker compose ps
```

Résultat attendu : Docker répond et les services déclarés sont visibles.

## Scénarios de panne

### Service arrêté

1. Lire le statut : `systemctl --user status hermes-openclaw-loop.service`.
2. Lire les logs : `journalctl --user -u hermes-openclaw-loop.service -n 100 --no-pager`.
3. Vérifier les permissions de `scripts/loop.sh`.
4. Relancer : `systemctl --user restart hermes-openclaw-loop.service`.

### OpenClaw ne répond plus

1. Vérifier `command -v openclaw`.
2. Vérifier `openclaw --version`.
3. Vérifier `openclaw gateway status` ou l'équivalent officiel.
4. Vérifier que la gateway écoute seulement en local.

### Hermes ne répond plus

1. Vérifier `command -v hermes`.
2. Vérifier `hermes --version`.
3. Vérifier `.env` local et les permissions.
4. Lire les logs systemd sans exposer de messages privés.

### MCP cassé

1. Vérifier la configuration MCP côté Hermes.
2. Vérifier les outils exposés côté OpenClaw.
3. Réduire temporairement la liste d'outils au minimum.
4. Tester une commande de liste MCP si disponible.

### Message invalide

1. Ne pas logger le contenu privé.
2. Logger seulement un identifiant technique ou un type d'erreur.
3. Répondre avec un message court et neutre.
4. Ajouter un cas de test après anonymisation.

### VPS sans ressources

1. Vérifier `free -h`.
2. Vérifier `df -h`.
3. Vérifier `top` ou `htop` si disponible.
4. Arrêter les services non essentiels.
5. Prévoir une taille VPS supérieure si le fournisseur IA ou les connecteurs demandent plus de ressources.

## Plan de tests

| Test | Commande | Résultat attendu |
| --- | --- | --- |
| Syntaxe boucle | `bash -n scripts/loop.sh` | Code 0 |
| Syntaxe santé | `bash -n scripts/healthcheck.sh` | Code 0 |
| Syntaxe sauvegarde | `bash -n scripts/backup-example.sh` | Code 0 |
| Service | `systemctl --user status hermes-openclaw-loop.service` | Actif sur VPS configuré |
| Logs | `journalctl --user -u hermes-openclaw-loop.service -n 50 --no-pager` | Pas de messages privés |
| OpenClaw | `openclaw gateway status` | Gateway locale OK |
| Hermes | `hermes --version` | Version affichée |

## Modèle d'incident

Créer un fichier dans `docs/incidents/` avec ce modèle :

```markdown
# Incident YYYY-MM-DD - Titre court

## Résumé

## Impact

## Chronologie UTC

## Cause probable

## Actions réalisées

## Actions préventives

## Données sensibles vérifiées

- [ ] Aucun token exposé.
- [ ] Aucun message privé copié.
- [ ] Aucune capture brute ajoutée.
```
