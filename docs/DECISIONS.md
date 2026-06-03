# Décisions d'architecture

Format ADR simplifié : contexte, décision, conséquences.

## ADR-001 - OpenClaw comme Gateway

Contexte : l'assistant doit recevoir et renvoyer des messages depuis Telegram,
puis WhatsApp plus tard.

Décision : utiliser OpenClaw comme gateway de messagerie.

Conséquences : OpenClaw concentre les intégrations de canaux. Les sessions et
tokens associés restent hors Git.

## ADR-002 - Hermes comme cerveau

Contexte : le projet doit séparer la messagerie de la logique agentique.

Décision : utiliser Hermes comme agent principal.

Conséquences : Hermes porte le choix du fournisseur IA, du modèle et du prompt.
OpenClaw reste un composant de transport.

## ADR-003 - MCP comme pont

Contexte : Hermes doit utiliser OpenClaw sans couplage direct fragile.

Décision : connecter Hermes à OpenClaw via MCP.

Conséquences : les outils exposés doivent être limités, documentés et testés.

## ADR-004 - Telegram avant WhatsApp

Contexte : WhatsApp implique souvent une session, un QR code et plus de risques
opérationnels.

Décision : livrer d'abord le MVP Telegram.

Conséquences : WhatsApp est repoussé après validation sécurité, sauvegardes et
runbook.

## ADR-005 - OpenClaw et MCP non exposés publiquement

Contexte : exposer la gateway ou MCP augmente fortement la surface d'attaque.

Décision : garder OpenClaw et MCP sur `127.0.0.1` ou derrière tunnel SSH.

Conséquences : l'accès distant passe par SSH, pas par un port public.

## ADR-006 - Boucle avec service systemd utilisateur

Contexte : le MVP doit tourner sans service root.

Décision : utiliser `hermes-openclaw-loop.service` comme unité systemd utilisateur.

Conséquences : l'unité utilise `%h`, ne contient pas `User=` et redémarre la
boucle avec `Restart=always`.

## ADR-007 - Secrets hors Git

Contexte : le dépôt est public ou lisible par un recruteur.

Décision : stocker les secrets uniquement dans `.env` local ou les dossiers de
configuration utilisateur protégés.

Conséquences : `.gitignore` bloque les secrets courants et `.env.example` ne
contient que des placeholders.

## ADR-008 - Sauvegarde simple puis chiffrée

Contexte : il faut pouvoir restaurer sans complexifier le MVP.

Décision : produire d'abord une archive locale avec checksum, puis exiger le
chiffrement avant stockage externe.

Conséquences : le script ne transfère rien automatiquement.

## ADR-009 - Docker Compose v2 seulement si nécessaire

Contexte : le MVP peut fonctionner avec des processus locaux.

Décision : garder Docker Compose v2 optionnel et utiliser seulement la commande
`docker compose`.

Conséquences : pas de dépendance conteneur imposée tant que plusieurs services
persistants ne sont pas nécessaires.

## ADR-010 - Monitoring, alerting et CI/CD plus tard

Contexte : la priorité est un MVP sécurisé et compréhensible.

Décision : repousser monitoring, alerting et CI/CD après validation manuelle.

Conséquences : la roadmap garde ces sujets dans les phases suivantes.
