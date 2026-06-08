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

Le diagnostic avancé reste strictement en lecture seule. Les commandes utilisées sont :

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
```

Ces commandes observent l'état local et ne modifient ni le réseau, ni le système de fichiers hors génération des rapports dans `outputs/reports`, ni Docker.

`/diag` ne doit pas être exposé publiquement sans authentification, car il peut contenir des informations de diagnostic locales.

Aucune commande `sudo`, destructive, modifiant le réseau ou destructive pour Docker n'est autorisée dans ce périmètre.

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

## Règles pour OpenAI API

L’API OpenAI ne doit pas exécuter de commandes.

Usage autorisé au début :

* résumer un rapport ;
* expliquer une erreur ;
* proposer une checklist ;
* classer les risques.

Usage interdit au début :

* décider seule d’une action ;
* exécuter une commande ;
* modifier la configuration système ;
* lancer des actions réseau agressives.

## Règles pour OpenClaw

OpenClaw devra être limité par une allowlist.

Au début, OpenClaw pourra seulement :

* lire un rapport ;
* appeler un script de diagnostic lecture seule ;
* demander un résumé IA.

OpenClaw ne devra pas pouvoir exécuter :

* commandes `sudo` ;
* commandes de suppression ;
* modifications réseau ;
* actions Docker destructives ;
* playbooks Ansible hors mode contrôle.

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

## Objectif sécurité à long terme

Le projet doit évoluer vers un lab capable de diagnostiquer et expliquer, mais pas de prendre le contrôle sans validation humaine.

## Vérification

Cherche les mots sensibles dans ton dépôt :

```bash
git grep -n "OPENAI_API_KEY\|password\|token\|secret\|PRIVATE KEY" || true
```
