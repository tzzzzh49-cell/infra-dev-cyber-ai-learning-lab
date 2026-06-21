# Sécurité du projet

## Objectif

Ce projet manipule des commandes systèmes et réseaux.  
La sécurité doit donc être prise en compte dès le début.

Le projet démarre volontairement en mode lecture seule.

## Principe principal

Aucune commande destructive ne doit être automatisée au stade actuel.

Le projet doit d’abord :

- observer ;
- diagnostiquer ;
- documenter ;
- expliquer ;
- proposer des pistes.

Il ne doit pas encore modifier automatiquement le système.

## Commandes autorisées au début

Les commandes autorisées doivent être non destructives.

Exemples :

```bash
ip addr
ip route
ss -tulpn
df -h
free -h
uptime
hostnamectl
systemctl status
journalctl --no-pager
```

## Commandes interdites au début

Les commandes suivantes ne doivent pas être automatisées :

```bash
rm -rf
mkfs
dd
reboot
shutdown
ip route del
ip addr flush
firewall-cmd --remove
docker rm
docker system prune
sudo sans justification
```


## Diagnostic réseau avancé v0.3.0

La version `v0.3.0` ajoute un diagnostic système/réseau structuré, mais le mode de sécurité reste strictement lecture seule.

Commandes utilisées par le module applicatif :

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

Le diagnostic lit aussi `/etc/resolv.conf` sans le modifier. Ces commandes observent l'état local et ne changent ni la configuration réseau, ni les conteneurs Docker, ni le disque. Chaque commande passe par une allowlist, sans `shell=True`, avec timeout court, durée mesurée et type d'erreur explicite (`command_not_found`, `timeout`, `non_zero_exit`, etc.).

`resolvectl` peut être absent selon la distribution ou le conteneur. Dans ce cas, le diagnostic tente des alternatives de lecture (`systemd-resolve --status`, puis `nmcli dev show`) et conserve une structure JSON exploitable si aucune commande n'est disponible.

Rappels obligatoires :

* `/diag` peut contenir des informations système et réseau et ne doit pas être exposé publiquement sans authentification ;
* aucune commande `sudo` n'est autorisée dans le diagnostic ;
* aucune commande destructive n'est autorisée ;
* aucune commande modifiant le réseau n'est autorisée ;
* aucune action Docker destructive comme `docker rm`, `docker stop` ou `docker system prune` n'est autorisée ;
* aucun secret réel ne doit être ajouté aux rapports générés.

## Règles pour les scripts

Chaque script doit respecter ces règles :

* être lisible ;
* avoir un nom clair ;
* afficher ce qu’il fait ;
* éviter les actions irréversibles ;
* ne pas contenir de secret ;
* pouvoir être relu avant exécution.

## Règles pour Docker

L’application doit d’abord être exposée localement.

Recommandation actuelle :

```text
127.0.0.1:8000
```

Éviter d’exposer publiquement `/diag` sans authentification.

## Protection des diagnostics HTTP

Les routes suivantes sont sensibles :

```text
/diag
/diag/export/json
/diag/export/markdown
```

Comportement attendu :

* elles exigent un token dans tous les environnements par défaut ;
* le serveur ne stocke pas de token clair : il attend `DIAG_ACCESS_TOKEN_HASH` ou `DIAG_ACCESS_TOKEN_HASH_FILE` ;
* les formats acceptés sont `sha256:<hash>` et `bcrypt:<hash>` ;
* le token fourni via `Authorization: Bearer <token>` ou `X-Diag-Token` est hashé puis comparé ;
* `DIAG_PROTECTION_DISABLED=true` désactive la protection uniquement en développement local explicite (`APP_ENV=local`, `dev`, `development` ou `test`) ;
* si aucun hash n'est configuré, les routes de diagnostic refusent l'accès au lieu de s'exposer sans protection.

Ne jamais commiter le token clair, le hash réel, un fichier de secret ou une configuration de reverse proxy contenant un secret. Les hashes doivent venir d'un gestionnaire de secrets comme Vault, AWS Secrets Manager, un secret Docker ou un fichier monté hors dépôt.

Génération :

```bash
python3 scripts/generate_diag_token.py --format sha256
python3 scripts/generate_diag_token.py --format bcrypt
```

Côté proxy, un secret runtime distinct peut être utilisé pour injecter `X-Diag-Token` après authentification basique ou OAuth. Dans ce cas, le proxy conserve le token clair dans son propre gestionnaire de secrets, tandis que l'application ne reçoit que `DIAG_ACCESS_TOKEN_HASH`.

## Timeouts et tentatives

Les commandes de diagnostic utilisent `DIAG_COMMAND_TIMEOUT`, avec une valeur
par défaut de `3` secondes. Le code plafonne cette valeur pour éviter qu'un
diagnostic bloqué immobilise l'API.

`DIAG_COMMAND_RETRIES` existe pour des environnements lents ou transitoires,
mais vaut `0` par défaut et reste plafonné. Les tentatives supplémentaires ne
doivent concerner que des commandes d'observation idempotentes.

## Règles pour OpenAI API

Il n'existe pas encore d'intégration OpenAI active dans le projet.

L’API OpenAI ne doit pas exécuter de commandes.

Usage autorisé au début :

* résumer un rapport ;
* extraire des risques depuis un rapport déjà généré ;
* proposer une checklist ;
* classer les risques.

Le flux préparatoire autorisé est :

```text
rapport Markdown/JSON -> résumé -> risques -> checklist humaine
```

La clé doit rester hors Git via variable d'environnement. `.env.ai.example` ne doit contenir aucune valeur réelle.

Usage interdit au début :

* décider seule d’une action ;
* exécuter une commande ;
* modifier la configuration système ;
* lancer des actions réseau agressives.

## Règles pour OpenClaw

Il n'existe pas encore d'intégration OpenClaw active dans le projet.

OpenClaw devra être limité par une allowlist et par une validation humaine.

Dans une future intégration, OpenClaw pourra seulement aider à :

* lire un rapport ;
* préparer l'appel d'un runbook lecture seule ;
* demander un résumé IA.

OpenClaw ne devra pas pouvoir exécuter :

* commandes automatiques sans validation humaine ;
* commandes `sudo` ;
* commandes de suppression ;
* modifications réseau ;
* actions Docker destructives ;
* playbooks Ansible hors mode contrôle.

La structure `openclaw/` reste documentaire et non active. Toute future activation devra respecter `openclaw/security-model.md`, `openclaw/allowlists/read-only.md` et les runbooks relus.

## Gestion des secrets

Ne jamais commiter :

* `.env`
* clés API
* tokens GitHub
* clés SSH privées
* mots de passe
* secrets OpenClaw

Utiliser plutôt :

* `.env.example`
* variables d’environnement
* GitHub Secrets plus tard

## Contrôles CI sécurité

La CI contient des contrôles non secrets :

* Bandit sur le code Python, avec seuil medium et confidence medium pour bloquer les failles applicatives significatives ;
* Hadolint sur `app/Dockerfile` ;
* Trivy sur l'image Docker construite en CI, bloquant sur les vulnérabilités critiques corrigibles ;
* Dependabot pour ouvrir des Pull Requests de mise à jour.

Les mainteneurs doivent surveiller les CVE des dépendances applicatives, de l'image de base et des GitHub Actions. Toute exception CVE doit être documentée avant merge.

Les images sont épinglées à une version précise et les GitHub Actions à un SHA.
Les tags d'images ne sont toutefois pas immuables : épingler aussi les digests
après validation avant un déploiement de production.

## Objectif sécurité à long terme

Le projet doit évoluer vers un lab capable de diagnostiquer et expliquer, mais pas de prendre le contrôle sans validation humaine.

## Vérification

Détecte les contenus sensibles probables sans afficher les valeurs :

```bash
find . \
  \( -path '*/.git' -o -path '*/.venv' -o -path '*/venv' -o -path '*/site-packages' -o -path '*/node_modules' -o -path '*/.ssh' -o -path '*/secrets' -o -path '*/.secrets' -o -path '*/outputs/backups' -o -path '*/outputs/raw' \) -prune -o \
  -type f -print \
  | xargs -r grep -IlE 'BEGIN OPENSSH PRIVATE KEY|BEGIN RSA PRIVATE KEY|OPENAI_API_KEY[[:space:]]*=|GITHUB_TOKEN[[:space:]]*=|github_pat_|ghp_|sk-[A-Za-z0-9_-]{20,}|CLOUDFLARE_API_TOKEN[[:space:]]*=|TAILSCALE_AUTHKEY[[:space:]]*=|AWS_SECRET_ACCESS_KEY[[:space:]]*=|RESTIC_PASSWORD[[:space:]]*=|POSTGRES_PASSWORD[[:space:]]*=|DATABASE_URL[[:space:]]*=' 2>/dev/null || true
```

La sortie contient uniquement des chemins de fichiers à examiner manuellement.
