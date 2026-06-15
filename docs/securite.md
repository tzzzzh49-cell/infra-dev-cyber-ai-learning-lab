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
ss -tulpn
df -h
free -h
docker ps --format '{{json .}}'
```

Le diagnostic lit aussi `/etc/resolv.conf` sans le modifier. Ces commandes observent l'état local et ne changent ni la configuration réseau, ni les conteneurs Docker, ni le disque.

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

* en local, avec exposition sur `127.0.0.1`, elles restent accessibles pour l'apprentissage ;
* si `DIAG_ACCESS_TOKEN` est défini, elles exigent un token via `Authorization: Bearer <token>` ou `X-Diag-Token` ;
* si `APP_ENV=vps` est actif, elles exigent `DIAG_ACCESS_TOKEN` ;
* si `APP_ENV=vps` est actif sans token configuré, elles refusent l'accès au lieu de s'exposer sans protection.

Ne jamais commiter la valeur réelle de `DIAG_ACCESS_TOKEN`. Les fichiers `.env*.example` doivent garder cette variable vide.

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

* Bandit sur le code Python, avec seuil medium pour éviter les faux positifs low liés aux commandes read-only encadrées ;
* Hadolint sur `app/Dockerfile` ;
* Trivy sur l'image Docker construite en CI.

Trivy est configuré en mode rapport non bloquant pour cette première intégration, afin de garder la CI fiable malgré les variations du flux CVE des images de base. Une future étape pourra rendre ce contrôle bloquant quand la politique d'exception sera documentée.

## Objectif sécurité à long terme

Le projet doit évoluer vers un lab capable de diagnostiquer et expliquer, mais pas de prendre le contrôle sans validation humaine.

## Vérification

Cherche les mots sensibles dans ton dépôt :

```bash
git grep -n "OPENAI_API_KEY\|password\|token\|secret\|PRIVATE KEY" || true
```
