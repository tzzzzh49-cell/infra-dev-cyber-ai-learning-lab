# Diagnostic réseau avancé v0.3.0

## Objectif

La version `v0.3.0` ajoute un diagnostic système/réseau avancé, structuré et exportable pour le lab local DevSecOps. L’objectif est d’observer l’état de la machine et de l’environnement Docker en **lecture seule**, sans modifier le réseau, les conteneurs, les fichiers système ou la configuration locale.

## Périmètre des données collectées

Le diagnostic collecte :

- informations système de base : hostname, plateforme, version plateforme, version Python ;
- interfaces réseau via `ip -j addr` ;
- routes réseau via `ip -j route` ;
- DNS via `/etc/resolv.conf` et `resolvectl dns` ou `resolvectl status` si disponible ;
- ports ouverts via `ss -tulpn` ;
- disque via `df -h` ;
- mémoire via `free -h` ;
- conteneurs Docker via `docker ps --format '{{json .}}'` ;
- métadonnées de sécurité confirmant le mode lecture seule.

## Commandes autorisées

Les commandes suivantes sont autorisées car elles observent l’état local sans le modifier :

```bash
ip -j addr
ip -j route
ss -tulpn
df -h
free -h
docker ps --format '{{json .}}'
resolvectl dns
resolvectl status
cat /etc/resolv.conf
```

Dans l’implémentation Python, `/etc/resolv.conf` est lu directement par la bibliothèque standard, sans commande `cat`.

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

Toute commande qui modifie le réseau, Docker, le firewall, les routes, les interfaces ou le système est hors périmètre.

## Structure JSON attendue

Le JSON produit suit une structure stable proche de :

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
    "interfaces": {
      "command": ["ip", "-j", "addr"],
      "available": true,
      "parsed": []
    },
    "routes": {
      "command": ["ip", "-j", "route"],
      "available": true,
      "parsed": []
    },
    "dns": {
      "resolv_conf": {},
      "resolvectl": {}
    },
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

## Formats d’export

Deux exports locaux sont disponibles :

- JSON : rapport structuré horodaté dans `outputs/reports` ;
- Markdown : rapport lisible horodaté dans `outputs/reports`.

Les exports sont générés par l’API locale et ne doivent pas être exposés publiquement sans authentification.

## Procédure d’utilisation

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

1. `make run` construit et démarre l’application puis attend `/health`.
2. `make diag` appelle `GET /diag` et affiche le diagnostic JSON.
3. `make diag-json` appelle `POST /diag/export/json` et crée un rapport JSON local.
4. `make diag-md` appelle `POST /diag/export/markdown` et crée un rapport Markdown local.
5. `make diagnostic-local` lance le script Bash local, génère un Markdown et sauvegarde aussi `/diag` en JSON si l’API répond.
6. `make reports` liste les fichiers présents dans `outputs/reports`.
7. `make down` arrête l’application Docker Compose du lab.

## Notes de sécurité

- Le diagnostic est strictement lecture seule.
- Aucune commande n’est lancée avec `shell=True` côté Python.
- Aucune commande `sudo` n’est utilisée.
- Aucune commande destructive Docker, système ou réseau n’est autorisée.
- `/diag` peut contenir des informations sensibles sur la machine locale et ne doit pas être exposé publiquement sans authentification.
- Aucun secret réel ne doit être ajouté dans les rapports, la documentation ou le code.

## Notes de reproductibilité Ubuntu 24.04.4 LTS Desktop

Ubuntu 24.04.4 LTS Desktop est la cible prioritaire. Les commandes `ip`, `ss`, `df`, `free`, `docker`, `curl` et `resolvectl` sont attendues sur un environnement Ubuntu standard préparé par `make bootstrap-ubuntu`.

Si une commande est absente ou indisponible, le diagnostic doit continuer et signaler l’indisponibilité dans le JSON/Markdown au lieu d’échouer brutalement.
