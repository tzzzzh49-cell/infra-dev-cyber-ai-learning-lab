# Runbook d'exploitation

## Architecture exploitée

```text
Telegram MVP / WhatsApp futur
        |
        v
OpenClaw Gateway local
        |
        v
MCP local limité
        |
        v
Hermes Agent
        |
        v
Fournisseur IA configuré
```

Tous les composants sensibles restent sur le VPS. OpenClaw et MCP ne sont pas
exposés publiquement.

## Statut rapide

```bash
cd ~/hermes-openclaw
git status --short
scripts/healthcheck.sh
```

Résultat attendu : pas de changement Git involontaire, commandes `openclaw` et
`hermes` disponibles, service utilisateur vérifiable si systemd user est actif.

## Vérification systemd

```bash
systemctl --user status hermes-openclaw-loop.service
systemctl --user is-enabled hermes-openclaw-loop.service
systemctl --user is-active hermes-openclaw-loop.service
```

Résultat attendu : le service est `enabled` et `active`. Systemd peut aussi
accepter `hermes-openclaw-loop` sans suffixe dans certaines commandes.

## Logs journalctl

```bash
journalctl --user -u hermes-openclaw-loop.service -n 100 --no-pager
journalctl --user -u hermes-openclaw-loop.service -f
```

Résultat attendu : logs techniques courts, sans contenu de messages privés, sans
token et sans QR code.

## Diagnostic OpenClaw

```bash
command -v openclaw
openclaw --help
openclaw gateway status
```

Résultat attendu : la CLI existe, l'aide s'affiche, la gateway renvoie un état.
Adapter les commandes selon la version officielle.

## Diagnostic Hermes

```bash
command -v hermes
hermes --version
```

Résultat attendu : la CLI existe et affiche une version. Éviter les tests LLM
coûteux ou fragiles dans le diagnostic de base.

## Diagnostic MCP

Points à vérifier :

- le serveur MCP est local ;
- seuls les outils nécessaires sont exposés ;
- Hermes voit les outils OpenClaw attendus ;
- aucune commande shell dangereuse n'est disponible ;
- les erreurs MCP sont lisibles dans les logs techniques.

Résultat attendu : Hermes peut demander à OpenClaw les événements nécessaires et
envoyer une réponse sans exposer le pont sur Internet.

## Diagnostic Docker / Compose si applicable

Docker Compose v2 est optionnel pour le MVP.
S'il est utilisé plus tard :

```bash
docker compose ps
docker compose logs --tail=100
```

Résultat attendu : les services persistants sont sains. Ne pas lancer de commande
destructive comme `docker system prune` dans une procédure de diagnostic standard.

## Scénarios de panne

### Service arrêté

1. Vérifier l'état : `systemctl --user status hermes-openclaw-loop.service`.
2. Lire les logs : `journalctl --user -u hermes-openclaw-loop.service -n 100`.
3. Relancer : `systemctl --user restart hermes-openclaw-loop.service`.

Résultat attendu : le service revient en `active` ou l'erreur est identifiable.

### OpenClaw ne répond plus

1. Vérifier `command -v openclaw`.
2. Vérifier `openclaw gateway status` si disponible.
3. Contrôler les permissions de `~/.openclaw`.
4. Redémarrer seulement le composant documenté par OpenClaw.

Résultat attendu : gateway à nouveau disponible sans réauthentification non
maîtrisée.

### Hermes ne répond plus

1. Vérifier `hermes --version`.
2. Vérifier `.env` local et fournisseur configuré.
3. Vérifier quotas, réseau sortant et modèle.
4. Redémarrer le service utilisateur.

Résultat attendu : Hermes répond aux commandes de base avant tout test LLM réel.

### MCP cassé

1. Vérifier la configuration des outils MCP.
2. Vérifier que les chemins CLI OpenClaw et Hermes sont corrects.
3. Réduire temporairement les outils exposés au minimum.
4. Lire les logs techniques sans messages privés.

Résultat attendu : le pont local est restauré avec une surface d'outils minimale.

### Message invalide

1. Ne pas logger le message brut.
2. Logger seulement un identifiant technique ou un type d'erreur.
3. Répondre par un message court et neutre.
4. Ajouter un cas de test si le format est reproductible sans donnée privée.

Résultat attendu : pas de fuite de contenu utilisateur dans les logs.

### VPS sans ressources

1. Vérifier `free -h` et `df -h`.
2. Vérifier les processus les plus consommateurs avec `ps` ou `top`.
3. Réduire la fréquence de boucle via `HERMES_OPENCLAW_LOOP_SLEEP`.
4. Prévoir monitoring et alerting dans une itération future.

Résultat attendu : le service redevient stable ou la limitation du VPS est
clairement identifiée.

## Plan de tests

| Test | Commande | Résultat attendu |
|---|---|---|
| Syntaxe scripts | `bash -n scripts/loop.sh` | Aucun message |
| Healthcheck local | `scripts/healthcheck.sh` | Code 0 si dépendances disponibles |
| Service | `systemctl --user status hermes-openclaw-loop.service` | `active` après installation |
| Logs | `journalctl --user -u hermes-openclaw-loop.service -n 50` | Pas de secret, pas de message privé |
| OpenClaw | `openclaw gateway status` | État lisible de la gateway |
| Hermes | `hermes --version` | Version affichée |
| Sauvegarde | `scripts/backup-example.sh` | Archive et checksum locaux en `chmod 600` |

## Modèle d'incident

Un modèle est préparé dans `docs/incidents/TEMPLATE.md`.
Créer un fichier daté par incident, sans secret et sans message privé.
