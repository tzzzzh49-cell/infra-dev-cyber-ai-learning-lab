# Runbook Hermes + OpenClaw Gateway

Ce runbook aide à exploiter le MVP Telegram sur VPS Ubuntu 24.04. Il ne remplace pas les tests réels OpenClaw, Hermes et MCP.

## Architecture exploitée

```text
Telegram -> OpenClaw Gateway local -> MCP local -> Hermes Agent -> fournisseur IA -> Hermes -> MCP -> OpenClaw -> Telegram
```

WhatsApp reste prévu plus tard.

## Commandes de statut rapide

```bash
cd ~/hermes-openclaw
git status --short
./scripts/healthcheck.sh
systemctl --user status hermes-openclaw-loop.service
```

Résultat attendu : pas de modification involontaire, healthcheck OK, service actif.

## Vérification systemd

```bash
systemctl --user daemon-reload
systemctl --user status hermes-openclaw-loop.service
systemctl --user is-enabled hermes-openclaw-loop.service
systemctl --user is-active hermes-openclaw-loop.service
```

Résultat attendu : unité chargée, enabled et active. Le nom sans suffixe `hermes-openclaw-loop` est souvent accepté par `systemctl`, mais la documentation utilise le nom complet.

## Logs journalctl

```bash
journalctl --user -u hermes-openclaw-loop.service --since "30 minutes ago"
journalctl --user -u hermes-openclaw-loop.service -n 50 --no-pager
```

Résultat attendu : logs techniques uniquement. Aucun message privé, token ou clé API.

## Diagnostic OpenClaw

```bash
command -v openclaw
openclaw --version
openclaw gateway status
```

Résultat attendu : CLI disponible, version lisible, gateway local contrôlable.

## Diagnostic Hermes

```bash
command -v hermes
hermes --version
```

Résultat attendu : CLI disponible et version lisible.

## Diagnostic MCP

Vérifier :

- la configuration MCP utilisée par Hermes ;
- l'URL OpenClaw locale ;
- la liste des outils autorisés ;
- les erreurs de schéma ;
- les permissions minimales.

```bash
# Exemple indicatif à adapter selon la CLI officielle.
hermes mcp list
hermes mcp inspect openclaw
```

Résultat attendu : le pont OpenClaw est déclaré, local et limité.

## Diagnostic Docker/Compose

Docker Compose est optionnel pour le MVP. Si utilisé :

```bash
docker compose version
docker compose ps
docker compose logs --no-color --tail=50
```

Résultat attendu : Compose v2 répond et les services optionnels sont sains.

## Scénarios de panne

### Service arrêté

Symptôme : aucune réponse automatique.

Actions :

```bash
systemctl --user status hermes-openclaw-loop.service
systemctl --user restart hermes-openclaw-loop.service
journalctl --user -u hermes-openclaw-loop.service -n 50 --no-pager
```

Résultat attendu : service relancé ou erreur explicite.

### OpenClaw ne répond plus

Actions :

```bash
openclaw gateway status
./scripts/healthcheck.sh
```

Résultat attendu : identifier si la CLI manque, si le gateway est arrêté ou si la configuration canal est cassée.

### Hermes ne répond plus

Actions :

```bash
hermes --version
./scripts/healthcheck.sh
journalctl --user -u hermes-openclaw-loop.service -n 50 --no-pager
```

Résultat attendu : distinguer absence CLI, problème fournisseur IA ou erreur MCP.

### MCP cassé

Actions :

```bash
# Adapter selon la CLI officielle.
hermes mcp list
hermes mcp inspect openclaw
```

Résultat attendu : trouver l'outil absent, une URL erronée ou une permission trop large.

### Message invalide

Actions :

- ne pas logger le contenu complet ;
- noter l'horodatage ;
- vérifier le format d'événement ;
- reproduire avec un message de test non sensible.

Résultat attendu : isoler le type d'événement sans exposer de données privées.

### VPS sans ressources

Actions :

```bash
free -h
df -h
top
systemctl --user status hermes-openclaw-loop.service
```

Résultat attendu : confirmer mémoire, disque ou CPU saturé, puis réduire la charge.

## Plan de tests

| Test | Commande | Résultat attendu |
|---|---|---|
| Dépôt propre | `git status --short` | Rien ou modifications connues |
| Scripts valides | `bash -n scripts/loop.sh scripts/healthcheck.sh scripts/backup-example.sh` | Code retour 0 |
| Healthcheck | `./scripts/healthcheck.sh` | OK si CLIs installées |
| systemd | `systemctl --user status hermes-openclaw-loop.service` | Service actif |
| Logs | `journalctl --user -u hermes-openclaw-loop.service -n 20 --no-pager` | Aucun secret |
| Telegram | Message de test non sensible | Réponse courte |
| Backup | `./scripts/backup-example.sh` | Archive locale et checksum |

## Modèle d'incident

Utiliser `docs/incidents/TEMPLATE.md` pour créer un rapport. Ne jamais inclure de message privé, token, clé API, IP publique non floutée ou QR code brut.
