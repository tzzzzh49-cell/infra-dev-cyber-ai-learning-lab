# Runbook OpenClaw — summarize report

Statut : proposition documentaire non active.

## Commande utilisateur

summarize report

## Objectif

Préparer le résumé d'un rapport Markdown ou JSON déjà généré et relu, sans exécuter de commande système.

Entrée attendue :

```text
outputs/reports/<rapport-revu>.md
outputs/reports/<rapport-revu>.json
```

## Action proposée après validation humaine

Un futur assistant contrôlé pourra lire le rapport fourni par l'utilisateur ou par un chemin validé, puis produire :

- résumé court ;
- risques observables ;
- points à vérifier ;
- checklist humaine.

## Interdits explicites

Ce runbook ne doit jamais :

- lancer `sudo` ;
- lancer `rm` ou suppression équivalente ;
- lancer `docker stop`, `docker rm` ou `docker compose down` ;
- modifier les routes avec `ip route add` ou `ip route del` ;
- modifier firewall, DNS, interface réseau ou configuration système ;
- appeler un outil cloud avec des secrets ;
- exécuter une action automatique sans validation humaine.

## Critère de réussite

La commande est réussie si :

1. aucun secret n'est inclus dans l'entrée ;
2. aucun shell libre n'est ouvert ;
3. aucune commande système n'est exécutée ;
4. la sortie contient un résumé, des risques et une checklist ;
5. la décision finale reste humaine.
