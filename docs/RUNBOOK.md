# Runbook Hermes + OpenClaw Gateway

## Architecture exploitée

```text
Telegram / WhatsApp -> OpenClaw Gateway -> MCP -> Hermes -> fournisseur IA -> OpenClaw -> utilisateur
```

Telegram est la cible MVP.
WhatsApp est prévu plus tard.
OpenClaw et MCP restent locaux au VPS.

## Commandes de statut rapide

```bash
cd ~/hermes-openclaw
scripts/healthcheck.sh
systemctl --user status hermes-openclaw-loop.service
journalctl --user -u hermes-openclaw-loop.service -n 50 --no-pager
```

Résultat attendu : état lisible, sans messages privés dans les logs.

## Vérification systemd

```bash
systemctl --user daemon-reload
systemctl --user status hermes-openclaw-loop.service
systemctl --user is-enabled hermes-openclaw-loop.service
```

Résultat attendu : service chargé et activé.
`systemctl --user status hermes-openclaw-loop` peut aussi fonctionner sans le suffixe `.service`.

## Logs journalctl

```bash
journalctl --user -u hermes-openclaw-loop.service -n 100 --no-pager
journalctl --user -u hermes-openclaw-loop.service -f
```

Résultat attendu : logs techniques seulement.
Ne pas journaliser de messages privés, tokens ou QR codes.

## Diagnostic OpenClaw

```bash
command -v openclaw
openclaw --version
openclaw gateway status
```

Résultat attendu : commande présente, version affichée, gateway locale avec statut exploitable.
Adapter aux commandes officielles de la version installée.

## Diagnostic Hermes

```bash
command -v hermes
hermes --version
```

Résultat attendu : commande présente et version affichée.
Un test LLM réel doit être validé manuellement car il utilise des secrets locaux et peut coûter de l'argent.

## Diagnostic MCP

Contrôles attendus :

```bash
ss -ltnp
curl -fsS http://127.0.0.1:18789/health
```

Résultat attendu : endpoint local accessible si la gateway expose une route de santé.
Si la route n'existe pas dans la version installée, utiliser la commande de statut officielle.

## Diagnostic Docker / Compose

Docker Compose est optionnel pour le MVP.
Si utilisé plus tard :

```bash
docker compose version
docker compose ps
docker compose logs --tail=100
```

Résultat attendu : services attendus visibles, logs sans secret.

## Scénarios de panne

### Service arrêté

Symptômes : aucune réponse automatique.

Actions :

```bash
systemctl --user status hermes-openclaw-loop.service
systemctl --user restart hermes-openclaw-loop.service
journalctl --user -u hermes-openclaw-loop.service -n 50 --no-pager
```

Résultat attendu : service relancé ou erreur claire.

### OpenClaw ne répond plus

Actions :

```bash
openclaw gateway status
ss -ltnp
```

Résultat attendu : gateway active localement.
Si elle est arrêtée, suivre la procédure officielle OpenClaw.

### Hermes ne répond plus

Actions :

```bash
hermes --version
scripts/healthcheck.sh
```

Résultat attendu : Hermes est installé et répond aux commandes de base.

### MCP cassé

Actions :

- vérifier l'URL `OPENCLAW_GATEWAY_URL` dans `.env` local ;
- vérifier les ports locaux ;
- vérifier les allowlists d'outils ;
- relire les logs techniques.

Résultat attendu : aucun port MCP exposé publiquement.

### Message invalide

Actions :

- ne pas logger le contenu privé ;
- logger uniquement un identifiant technique anonymisé si nécessaire ;
- ignorer le message ou répondre avec un message court de fallback.

Résultat attendu : pas de crash de boucle.

### VPS sans ressources

Actions :

```bash
free -h
df -h
uptime
systemctl --user status hermes-openclaw-loop.service
```

Résultat attendu : identifier RAM, disque ou charge CPU insuffisants.

## Plan de tests

| Test | Commande | Résultat attendu |
|---|---|---|
| Dépôt propre | `git status --short` | aucune modification inattendue |
| Syntaxe boucle | `bash -n scripts/loop.sh` | code retour `0` |
| Syntaxe santé | `bash -n scripts/healthcheck.sh` | code retour `0` |
| Syntaxe backup | `bash -n scripts/backup-example.sh` | code retour `0` |
| Santé locale | `scripts/healthcheck.sh` | diagnostics lisibles |
| Service | `systemctl --user status hermes-openclaw-loop.service` | actif ou erreur exploitable |
| Logs | `journalctl --user -u hermes-openclaw-loop.service -n 50 --no-pager` | aucun secret |
| OpenClaw | `openclaw gateway status` | statut local |
| Hermes | `hermes --version` | version affichée |
| Backup | `scripts/backup-example.sh` | archive locale et checksum |

## Modèle d'incident

Créer un fichier dans `docs/incidents/` avec ce modèle :

```markdown
# Incident YYYY-MM-DD - titre court

## Impact

## Heure de début

## Heure de fin

## Symptômes

## Actions réalisées

## Cause probable

## Correctif

## Prévention

## Données sensibles vérifiées

- [ ] Aucun token dans les logs.
- [ ] Aucun message privé publié.
- [ ] Aucune capture brute publiée.
```
