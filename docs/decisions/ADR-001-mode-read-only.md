# ADR-001 — Démarrer en mode lecture seule

## Statut

Accepté

## Contexte

Le projet vise à apprendre Linux, les réseaux, Docker, FastAPI, l’automatisation et la cybersécurité défensive.

Certaines commandes systèmes peuvent modifier ou endommager une machine si elles sont mal utilisées.

Comme le projet est encore en phase d’apprentissage, il est préférable de commencer par des diagnostics non destructifs.

## Décision

Le projet démarre en mode lecture seule.

Les premières fonctionnalités doivent uniquement :
- lire l’état du système ;
- afficher des informations ;
- produire des rapports ;
- aider à comprendre ;
- proposer des pistes d’amélioration.

Les scripts ne doivent pas modifier la configuration réseau, supprimer des fichiers ou exécuter des actions irréversibles.

## Commandes acceptées au départ

Exemples :

```bash
ip addr
ip route
ss -tulpn
df -h
free -h
uptime
hostnamectl
```

## Commandes refusées au départ

Exemples :

```bash
rm -rf
mkfs
dd
ip route del
docker system prune
reboot
shutdown
```

## Conséquences positives

- le projet est plus sûr ;
- les erreurs sont moins dangereuses ;
- la documentation est plus claire ;
- le projet montre une démarche cybersécurité défensive.

## Conséquences négatives

- certaines automatisations seront plus lentes à développer ;
- le projet ne corrigera pas automatiquement les problèmes au début ;
- certaines actions devront rester manuelles.

## Évolution possible

Une future version pourra ajouter des actions correctives, mais uniquement avec :

- validation humaine ;
- logs ;
- sauvegarde préalable ;
- documentation ;
- tests ;
- allowlist stricte.
