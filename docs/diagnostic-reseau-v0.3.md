# Diagnostic réseau avancé v0.3.0

## Objectif

La version `v0.3.0` ajoute un diagnostic système/réseau structuré en lecture seule pour aider à comprendre l'état local du lab sans modifier la machine. Le diagnostic est disponible via l'endpoint local `/diag`, via des exports API JSON/Markdown et via le script local `scripts/diagnostic_local.sh`.

## Périmètre des données collectées

Le rapport collecte uniquement des informations observables localement :

- informations système : hostname, plateforme, version plateforme, version Python ;
- interfaces réseau ;
- routes réseau ;
- DNS depuis `/etc/resolv.conf`, `resolvectl` si disponible et des alternatives read-only selon la distribution ;
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
systemd-resolve --status
nmcli dev show
ss -tulpn
df -h
free -h
docker ps --format '{{json .}}'
```

Le fichier `/etc/resolv.conf` est lu sans modification. Toutes les commandes sont exécutées sans shell, avec timeout court, durée mesurée et type d'erreur explicite. Les commandes DNS alternatives sont tentées seulement si la commande précédente ne répond pas correctement.

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
    "mode": "read-only"
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
    "dns": {"resolv_conf": {}, "resolver_commands": {}},
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

Chaque résultat de commande inclut la commande exécutée, la disponibilité, le code retour, `stdout`, `stderr`, le timeout configuré, la durée d'exécution, le nombre de tentatives et un type d'erreur stable.

## Formats d'export

Les exports sont écrits dans `outputs/reports` :

- JSON : `diagnostic-network-YYYY-MM-DD-HHMMSS-microseconds.json` ;
- Markdown : `diagnostic-network-YYYY-MM-DD-HHMMSS-microseconds.md` ;
- script local : `diagnostic-YYYY-MM-DD-HHMMSS.md` et, si l'API répond, `diagnostic-api-YYYY-MM-DD-HHMMSS.json`.

## Procédure d'utilisation

```bash
python3 scripts/generate_diag_token.py
export APP_ENV=lab
export DIAG_CLIENT_TOKEN='<JETON_AFFICHE_PAR_LE_SCRIPT>'
export DIAG_ACCESS_TOKEN_HASH='<HASH_AFFICHE_PAR_LE_SCRIPT>'
make run
make diag
make diag-json
make diag-md
make diagnostic-local
make reports
make down
```

Détail :

1. Le script génère un jeton client et son hash `sha256`.
2. `APP_ENV=lab` active le mode lab local. En `APP_ENV=vps`, le jeton partagé
   est refusé et l'API attend OIDC.
3. `make run` construit et démarre l'application localement.
4. `make diag` interroge `GET /diag` et retourne une vue HTTP minimisée
   (`metadata`, `checks`, `security`), sans sortie brute de commande.
5. `make diag-json` appelle `POST /diag/export/json`.
6. `make diag-md` appelle `POST /diag/export/markdown`.
7. `make diagnostic-local` génère un rapport Markdown local et tente de sauvegarder la réponse JSON de `/diag` si l'API est disponible.
8. `make reports` liste les fichiers présents dans `outputs/reports` sans échouer si le dossier est absent.
9. `make down` arrête l'application.

## Protection des routes sensibles

`/diag`, `/diag/export/json` et `/diag/export/markdown` exigent une
authentification par défaut.

Configuration attendue en lab local :

- générer un jeton aléatoire avec `python3 scripts/generate_diag_token.py` ;
- définir `APP_ENV=lab` ;
- fournir le hash via `DIAG_ACCESS_TOKEN_HASH` ou monter un fichier via `DIAG_ACCESS_TOKEN_HASH_FILE` ;
- appeler les routes sensibles avec `Authorization: Bearer <token>` ou `X-Diag-Token: <token>` ;
- garder l'API liée à `127.0.0.1` derrière un reverse proxy HTTPS authentifié.

En VPS (`APP_ENV=vps`), le jeton partagé local est refusé. Les routes sensibles
attendent un JWT OIDC signé, avec permission `diagnostic:read` pour `/diag` et
`diagnostic:export` plus MFA pour les exports.

Pour un développement strictement local, `DIAG_PROTECTION_DISABLED=true` peut désactiver la protection seulement si `APP_ENV` vaut `local`, `dev`, `development` ou `test`. Cette variable est ignorée en VPS/production.

En lab local, si aucun hash n'est configuré, les routes de diagnostic renvoient une erreur et ne publient pas le diagnostic.

## Notes de sécurité

- Le mode reste strictement lecture seule.
- Les commandes sont exécutées sans `shell=True` côté Python.
- Les timeouts courts évitent qu'une commande bloque indéfiniment.
- `DIAG_COMMAND_TIMEOUT` vaut `3` secondes par défaut et reste plafonné.
- `DIAG_COMMAND_RETRIES` vaut `0` par défaut et reste réservé aux commandes d'observation idempotentes.
- `/diag` peut exposer des informations locales sensibles et ne doit pas être exposé publiquement sans authentification.
- Les exports `/diag/export/json` et `/diag/export/markdown` suivent la même règle de protection que `/diag`.
- Un seul diagnostic est exécuté à la fois ; un appel concurrent reçoit HTTP 429.
- Les 20 exports les plus récents sont conservés pour chaque format JSON et Markdown.
- Aucun secret réel ne doit être ajouté aux rapports, scripts ou exemples de configuration.

## Notes de reproductibilité Ubuntu 26.04 LTS Server

Ubuntu 26.04 LTS Server est la cible prioritaire. Les commandes `ip`, `ss`, `df`, `free`, `docker`, `curl` et `resolvectl` sont attendues sur cette cible après bootstrap du lab, avec `systemd-resolve` ou `nmcli` comme alternatives DNS possibles. Si une commande est absente, le diagnostic ne doit pas échouer brutalement : la section correspondante indique l'indisponibilité et conserve une structure JSON exploitable.
