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

* en VPS, elles exigent un JWT OIDC dans `Authorization: Bearer` ;
* l'API valide issuer, audience, signature, expiration, durée maximale et taille
  de clé à chaque requête ;
* seuls les algorithmes asymétriques RS, PS et ES forts sont acceptés ;
* les routes refusent l'accès par défaut et exigent une permission explicite :
  `diagnostic:read` pour `/diag`, `diagnostic:export` pour les exports ;
* côté serveur, le rôle `partner` accorde seulement `diagnostic:read`, le rôle
  `admin` accorde les deux permissions et le rôle `user` n'en accorde aucune ;
* un scope OIDC vérifié portant exactement le nom d'une permission peut aussi
  l'accorder ; les rôles et scopes inconnus sont ignorés ;
* les exports exigent en plus un second facteur vérifié (`amr=mfa` ou une valeur
  `acr` explicitement admise) en environnement VPS ;
* `DIAG_PROTECTION_DISABLED=true` désactive la protection uniquement en développement local explicite (`APP_ENV=local`, `dev`, `development` ou `test`) ;
* le jeton partagé historique reste accepté uniquement en environnement local.

Ne jamais commiter le secret client OIDC, la clé de cookie, un token ou une
configuration contenant un secret. OAuth2 Proxy lit ses secrets depuis des
fichiers privés montés en lecture seule.

Génération du jeton partagé, pour le lab local uniquement :

```bash
python3 scripts/generate_diag_token.py
```

OAuth2 Proxy gère Authorization Code avec PKCE S256 et transmet un ID token à
l'API. L'API ne fait confiance ni au rôle ni à l'identité déclarés par un simple
en-tête de gateway : elle les extrait uniquement du JWT validé.

## Autorisation des ressources (BOLA/IDOR)

L'ID utilisateur fiable est le claim `sub` du JWT validé. Une route qui reçoit
un identifiant de ressource doit charger l'objet côté serveur, puis appeler
`authorize_resource_access` avec le propriétaire et l'ACL enregistrés avec cet
objet. Un `owner_id` ou une ACL envoyés par le client ne doivent jamais servir à
autoriser l'accès. Le garde vérifie aussi la permission de l'action et renvoie
404 si l'utilisateur n'est ni propriétaire ni membre de l'ACL, ce qui limite
l'énumération des objets d'autres utilisateurs.

L'API actuelle n'accepte encore aucun identifiant de ressource : `report_id` est
uniquement renvoyé après un export et aucune route ne permet de le relire.

## Timeouts et tentatives

Les commandes de diagnostic utilisent `DIAG_COMMAND_TIMEOUT`, avec une valeur
par défaut de `3` secondes. Le code plafonne cette valeur pour éviter qu'un
diagnostic bloqué immobilise l'API.

`DIAG_COMMAND_RETRIES` existe pour des environnements lents ou transitoires,
mais vaut `0` par défaut et reste plafonné. Les tentatives supplémentaires ne
doivent concerner que des commandes d'observation idempotentes.

Un seul diagnostic est exécuté à la fois. Un appel concurrent reçoit HTTP 429.
Une identité authentifiée, ou à défaut son adresse IP validée par le proxy, est
limitée à cinq diagnostics par minute. Ce quota est conservé en mémoire et
suppose un seul worker Uvicorn.
Les exports serveur conservent les 20 fichiers les plus récents par format.

L'API expose le mécanisme OIDC Bearer dans OpenAPI en local. En mode VPS,
Swagger, ReDoc et le schéma OpenAPI sont désactivés. Nginx retire les en-têtes
d'identité forgés par le client avant de transmettre la requête.

## Gestion des secrets

Ne jamais commiter :

* `.env`
* clés API
* tokens GitHub
* clés SSH privées
* mots de passe

Utiliser plutôt :

* `.env.example`
* GitHub Secrets pour les valeurs strictement nécessaires aux GitHub Actions ;
* un coffre de production comme Vault ou AWS Secrets Manager, injecté sous
  forme de fichier privé monté en lecture seule ;
* des variables d'environnement uniquement pour les paramètres non secrets.

Le jeton automatique `GITHUB_TOKEN` conserve les permissions minimales définies
dans le workflow. Aucun secret de production ne doit être rendu disponible à
une Pull Request provenant d'un fork.

## Rotation et révocation

Les certificats mTLS de service durent un an. `make mtls-check` bloque désormais
un démarrage public lorsqu'un certificat expire dans moins de 30 jours. Planifier
ce contrôle quotidien dans la supervision du VPS et effectuer la rotation dans
une fenêtre de maintenance en conservant l'ancien jeu pour rollback.

Pour les secrets OIDC, API et partenaires, définir dans le coffre une échéance
de 90 jours maximum, ou la durée plus courte imposée par le fournisseur. Si un
secret est compromis : le révoquer d'abord chez le fournisseur ou l'IdP, couper
le rôle ou le compte concerné, créer une nouvelle valeur, redéployer, puis
vérifier les journaux. Ne jamais copier l'ancienne ou la nouvelle valeur dans
un ticket, une Pull Request ou un journal.

Le renouvellement automatique sera confié au coffre ou au client ACME choisi en
production. Le dépôt ne remplace pas automatiquement une CA mTLS : une rotation
aveugle couperait la communication entre Nginx et l'API.

## TLS public

Nginx accepte uniquement TLS 1.2 et TLS 1.3. Après chaque déploiement ou
renouvellement public, vérifier la chaîne sans afficher de clé privée :

```bash
openssl s_client -connect <LAB_DOMAIN>:443 -servername <LAB_DOMAIN> \
  -verify_return_error </dev/null
```

Le certificat Let's Encrypt ou équivalent et son renouvellement restent gérés
hors dépôt par le client ACME du VPS.

## Contrôles CI sécurité

La CI contient des contrôles non secrets :

* Bandit sur le code Python, avec seuil medium et confidence medium pour bloquer les failles applicatives significatives ;
* Hadolint sur `app/Dockerfile` ;
* Gitleaks sur l'historique Git pour détecter les secrets committés ;
* Trivy sur l'image Docker construite en CI, bloquant sur les vulnérabilités élevées et critiques corrigibles ;
* OWASP ZAP sur une instance locale éphémère, avec échec sur les familles
  d'injection, SSRF, XXE et traversée de chemin configurées dans `.zap/rules.tsv` ;
* Dependabot pour ouvrir des Pull Requests de mise à jour.

Le scan ZAP est actif : il attaque uniquement l'API éphémère du runner CI, jamais
une URL de production ou un service tiers.

Les mainteneurs doivent surveiller les CVE des dépendances applicatives, de l'image de base et des GitHub Actions. Toute exception CVE doit être documentée avant merge.

Les images sont épinglées à une version précise et les GitHub Actions à un SHA.
Les tags d'images ne sont toutefois pas immuables : épingler aussi les digests
après validation avant un déploiement de production.

## Revue et protection de branche

Dans les réglages GitHub de `master`, activer une règle qui exige une Pull
Request, au moins une approbation, la réapprobation après nouveau commit et la
réussite de tous les jobs de `.github/workflows/ci.yml`. Interdire aussi les
force-push et la suppression de la branche. Ces réglages vivent sur GitHub et ne
peuvent pas être imposés par un fichier du dépôt.

## Objectif sécurité à long terme

Le projet doit évoluer vers un lab capable de diagnostiquer et expliquer, mais pas de prendre le contrôle sans validation humaine.

## Vérification

Détecte les contenus sensibles probables sans afficher les valeurs :

```bash
find . \
  \( -path '*/.git' -o -path '*/.venv' -o -path '*/venv' -o -path '*/site-packages' -o -path '*/node_modules' -o -path '*/.ssh' -o -path '*/secrets' -o -path '*/.secrets' -o -path '*/outputs/backups' -o -path '*/outputs/raw' \) -prune -o \
  -type f -print \
  | xargs -r grep -IlE 'BEGIN OPENSSH PRIVATE KEY|BEGIN RSA PRIVATE KEY|GITHUB_TOKEN[[:space:]]*=|github_pat_|ghp_|sk-[A-Za-z0-9_-]{20,}|CLOUDFLARE_API_TOKEN[[:space:]]*=|TAILSCALE_AUTHKEY[[:space:]]*=|AWS_SECRET_ACCESS_KEY[[:space:]]*=|RESTIC_PASSWORD[[:space:]]*=|POSTGRES_PASSWORD[[:space:]]*=|DATABASE_URL[[:space:]]*=' 2>/dev/null || true
```

La sortie contient uniquement des chemins de fichiers à examiner manuellement.
