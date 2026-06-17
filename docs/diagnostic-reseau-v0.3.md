# Diagnostic réseau avancé v0.3.0

## Objectif

La version `v0.3.0` ajoute un diagnostic système/réseau structuré en lecture seule pour aider à comprendre l'état local du lab sans modifier la machine. Le diagnostic est disponible via l'endpoint local `/diag`, via des exports API JSON/Markdown et via le script local `scripts/diagnostic_local.sh`.

## Périmètre des données collectées

Le rapport collecte uniquement des informations observables localement :

- informations système : hostname, plateforme, version plateforme, version Python ;
- interfaces réseau ;
- routes réseau ;
- DNS depuis `/etc/resolv.conf` et `resolvectl` si disponible ;
- ports ouverts ;
- espace disque ;
- mémoire ;
- conteneurs Docker visibles par `docker ps` ;
- métadonnées de sécurité confirmant le mode lecture seule.

## Commandes autorisées

Les commandes utilisées par `app/diagnostics.py` sont non destructives :

```bash
ip -j addr
ip -j route
resolvectl dns
resolvectl status
ss -tulpn
df -h
free -h
docker ps --format '{{json .}}'
```

Le fichier `/etc/resolv.conf` est lu sans modification.

## Commandes interdites

La version `v0.3.0` n'autorise pas :

```bash
sudo
rm -rf
mkfs
dd
reboot
shutdown
ip route del
ip addr flush
firewall-cmd --remove
docker rm
docker stop
docker system prune
```

Plus généralement, aucune commande destructive, aucune modification réseau et aucune action Docker destructive ne doit être ajoutée au diagnostic.

## Structure JSON attendue

La structure reste stable autour des sections principales suivantes :

```json
{
  "metadata": {
    "schema_version": "0.3.0",
    "generated_at_utc": "...",
    "mode": "read-only",
    "command_timeout_seconds": 3.0
  },
  "system": {
    "hostname": "...",
    "platform": "...",
    "platform_version": "...",
    "python_version": "..."
  },
  "network": {
    "interfaces": {"command": ["ip", "-j", "addr"], "available": true, "parsed": []},
    "routes": {"command": ["ip", "-j", "route"], "available": true, "parsed": []},
    "dns": {"resolv_conf": {}, "resolvectl": {}},
    "ports": {}
  },
  "resources": {
    "disk": {},
    "memory": {}
  },
  "docker": {},
  "security": {
    "read_only": true,
    "destructive_commands_used": false
  }
}
```

Chaque résultat de commande inclut la commande exécutée, la disponibilité, le code retour, `stdout`, `stderr`, l'information de timeout et le nombre de tentatives.

## Formats d'export

Les exports sont écrits dans `outputs/reports` :

- JSON : `diagnostic-network-YYYY-MM-DD-HHMMSS-microseconds.json` ;
- Markdown : `diagnostic-network-YYYY-MM-DD-HHMMSS-microseconds.md` ;
- script local : `diagnostic-YYYY-MM-DD-HHMMSS.md` et, si l'API répond, `diagnostic-api-YYYY-MM-DD-HHMMSS.json`.

## Procédure d'utilisation

```bash
make run
make diag
make diag-json
make diag-md
make diagnostic-local
make reports
make down
```

Détail :

1. `make run` construit et démarre l'application localement.
2. `make diag` interroge `GET /diag`.
3. `make diag-json` appelle `POST /diag/export/json`.
4. `make diag-md` appelle `POST /diag/export/markdown`.
5. `make diagnostic-local` génère un rapport Markdown local et tente de sauvegarder la réponse JSON de `/diag` si l'API est disponible.
6. `make reports` liste les fichiers présents dans `outputs/reports` sans échouer si le dossier est absent.
7. `make down` arrête l'application.

## Protection des routes sensibles

En local, sans `DIAG_ACCESS_TOKEN`, sans `DIAG_ACCESS_TOKEN_SHA256` et hors mode VPS, les commandes `make diag`, `make diag-json` et `make diag-md` restent utilisables sur `127.0.0.1`.

Pour un environnement VPS ou préproduction :

- définir `APP_ENV=vps` ;
- définir de préférence `DIAG_ACCESS_TOKEN_SHA256` dans un fichier `.env` privé non commité ;
- garder le token client clair seulement dans la session opérateur ou dans l'environnement privé du reverse proxy ;
- appeler les routes sensibles avec `Authorization: Bearer <token>` ou `X-Diag-Token: <token>` ;
- garder l'API liée à `127.0.0.1` derrière un reverse proxy HTTPS authentifié.

Si `APP_ENV=vps` est actif mais qu'aucun token ni hash n'est configuré, `/diag`, `/diag/export/json` et `/diag/export/markdown` renvoient une erreur et ne publient pas le diagnostic.

Exemples complets : `docs/api-examples.md`.

## Timeout configurable

`DIAG_COMMAND_TIMEOUT` vaut `3` secondes par défaut. Il peut être augmenté pour
une VM lente, mais reste plafonné par le code applicatif. `DIAG_COMMAND_RETRIES`
vaut `0` par défaut et doit rester réservé à des commandes d'observation
idempotentes.

## Notes de sécurité

- Le mode reste strictement lecture seule.
- Les commandes sont exécutées sans `shell=True` côté Python.
- Les timeouts courts évitent qu'une commande bloque indéfiniment.
- `/diag` peut exposer des informations locales sensibles et ne doit pas être exposé publiquement sans authentification.
- Les exports `/diag/export/json` et `/diag/export/markdown` suivent la même règle de protection que `/diag`.
- Aucun secret réel ne doit être ajouté aux rapports, scripts ou exemples de configuration.

## Notes de reproductibilité Ubuntu 26.04 LTS Server

Ubuntu 26.04 LTS Server est la cible prioritaire. Les commandes `ip`, `ss`, `df`, `free`, `docker`, `curl` et `resolvectl` sont attendues sur cette cible après bootstrap du lab. Si une commande est absente, le diagnostic ne doit pas échouer brutalement : la section correspondante indique l'indisponibilité et conserve une structure JSON exploitable.
