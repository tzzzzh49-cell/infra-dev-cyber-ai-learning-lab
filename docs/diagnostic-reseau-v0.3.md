# Diagnostic réseau avancé v0.3.0

## Objectif

Le diagnostic réseau avancé v0.3.0 enrichit le lab avec une collecte structurée, locale et strictement en lecture seule des informations système, réseau, ressources et Docker utiles au dépannage défensif.

Il vise à produire des rapports reproductibles sur Ubuntu 24.04.4 LTS Desktop sans modifier la machine, le réseau ou Docker.

## Périmètre des données collectées

Le rapport collecte :

- métadonnées du rapport : version de schéma, date UTC, mode lecture seule ;
- informations système : hostname, plateforme, version plateforme, version Python ;
- interfaces réseau ;
- routes réseau ;
- configuration DNS locale ;
- ports ouverts ;
- espace disque ;
- mémoire ;
- conteneurs Docker visibles via `docker ps` ;
- indicateurs de sécurité confirmant l'absence de commandes destructives.

## Commandes autorisées

Les commandes utilisées sont des commandes d'observation :

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

La lecture du fichier `/etc/resolv.conf` est également autorisée.

## Commandes interdites

Les commandes suivantes restent interdites dans ce diagnostic :

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

Plus généralement, toute commande qui supprime, redémarre, modifie le réseau, modifie Docker ou élève les privilèges est exclue.

## Structure JSON attendue

La structure cible est stable et organisée par sections :

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

## Formats d'export

Deux formats sont disponibles localement :

- JSON : export structuré pour analyse automatisée ;
- Markdown : rapport lisible pour relecture humaine.

Les fichiers sont générés dans `outputs/reports` avec un nom horodaté.

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

- `make run` construit, démarre l'application et attend `/health` ;
- `make diag` affiche le diagnostic JSON retourné par `GET /diag` ;
- `make diag-json` demande un export JSON via `POST /diag/export/json` ;
- `make diag-md` demande un export Markdown via `POST /diag/export/markdown` ;
- `make diagnostic-local` génère un rapport local Markdown et tente de sauvegarder la réponse `/diag` si l'API répond ;
- `make reports` liste les rapports présents dans `outputs/reports` ;
- `make down` arrête l'application.

## Notes de sécurité

- Le diagnostic reste en lecture seule.
- Les commandes sont exécutées sans `shell=True` côté Python.
- Aucune commande `sudo` n'est utilisée.
- Aucune commande destructive Docker ou réseau n'est utilisée.
- `/diag` peut exposer des informations système et ne doit pas être publié sans authentification.
- Aucun secret réel ne doit être stocké dans les rapports.

## Notes de reproductibilité Ubuntu 24.04.4 LTS Desktop

Ubuntu 24.04.4 LTS Desktop est la cible prioritaire. Les commandes `ip`, `ss`, `df`, `free`, `resolvectl`, `docker`, `curl`, `make`, `shellcheck` et Python 3 sont couvertes par le bootstrap Ubuntu du projet.

Certaines commandes peuvent être absentes ou retourner une erreur selon l'environnement local. Le diagnostic capture ces cas sans interrompre l'exécution, afin que le rapport reste exploitable même si Docker ou l'API locale ne sont pas démarrés.
