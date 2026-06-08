# Diagnostic réseau avancé v0.3.0

## Objectif

Le diagnostic réseau avancé `v0.3.0` enrichit le lab local avec une collecte structurée, reproductible et strictement lecture seule des informations système, réseau, ressources et Docker.

Il sert à apprendre le diagnostic défensif sans modifier la machine, sans utiliser de secret et sans exposer publiquement les informations collectées.

## Périmètre des données collectées

Le rapport collecte :

- métadonnées du rapport : version de schéma, date UTC, mode lecture seule ;
- informations système : hostname, plateforme, version plateforme, version Python ;
- interfaces réseau ;
- routes réseau ;
- DNS via `/etc/resolv.conf` et `resolvectl` si disponible ;
- ports ouverts ;
- espace disque ;
- mémoire ;
- conteneurs Docker visibles via `docker ps` ;
- indicateurs de sécurité confirmant le mode lecture seule.

## Commandes autorisées

Les commandes utilisées par `app/diagnostics.py` et le script local sont non destructives :

```bash
ip -j addr
ip -j route
cat /etc/resolv.conf
resolvectl dns
resolvectl status
ss -tulpn
df -h
free -h
docker ps --format '{{json .}}'
hostname
uname -a
curl --max-time 3 http://127.0.0.1:8000/diag
```

## Commandes interdites

Les commandes suivantes restent interdites dans ce périmètre :

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
docker compose down --volumes
```

Toute commande modifiant le réseau, supprimant des ressources Docker ou altérant l'état du système est hors périmètre.

## Structure JSON attendue

Structure de haut niveau :

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
    "interfaces": {},
    "routes": {},
    "dns": {},
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

Chaque commande expose une structure stable avec la commande exécutée, sa disponibilité, son code retour, stdout, stderr et l'état de timeout. Les commandes JSON comme `ip -j addr`, `ip -j route` et `docker ps --format '{{json .}}'` ajoutent aussi une clé `parsed`.

## Formats d'export

Les exports sont écrits localement dans `outputs/reports` :

- JSON horodaté : `diagnostic-network-YYYY-MM-DD-HHMMSS.json` ;
- Markdown horodaté : `diagnostic-network-YYYY-MM-DD-HHMMSS.md` ;
- JSON API récupéré par le script local : `diagnostic-api-YYYY-MM-DD-HHMMSS.json`.

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

1. `make run` construit et démarre l'API locale puis attend `/health` ;
2. `make diag` interroge `GET /diag` ;
3. `make diag-json` appelle `POST /diag/export/json` ;
4. `make diag-md` appelle `POST /diag/export/markdown` ;
5. `make diagnostic-local` génère un rapport Markdown local et tente de sauvegarder `/diag` en JSON si l'API est disponible ;
6. `make reports` liste les fichiers présents dans `outputs/reports` ;
7. `make down` arrête l'application.

## Notes de sécurité

- `/diag` contient potentiellement des informations locales sensibles et ne doit pas être exposé publiquement sans authentification.
- Les exports restent dans `outputs/reports` par défaut.
- Aucun secret réel n'est nécessaire.
- Aucune commande `sudo`, destructive, modifiant le réseau ou détruisant des ressources Docker n'est autorisée.
- Les commandes sont exécutées sans `shell=True` dans le module Python.

## Notes de reproductibilité Ubuntu 24.04.4 LTS Desktop

La cible prioritaire reste Ubuntu 24.04.4 LTS Desktop. Les commandes `ip`, `ss`, `df`, `free`, `resolvectl`, `docker`, `curl` et `timeout` sont courantes sur cette cible après bootstrap du lab. Le diagnostic tolère toutefois les commandes absentes : une commande manquante est reportée dans le JSON au lieu de faire échouer l'API.
