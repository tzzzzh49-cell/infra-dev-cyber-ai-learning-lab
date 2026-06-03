# Décisions techniques

Format ADR court : contexte, décision, conséquences.

## ADR-001 - OpenClaw comme Gateway

Contexte : le projet doit recevoir et envoyer des messages depuis plusieurs canaux.

Décision : utiliser OpenClaw comme Gateway.

Conséquences : Telegram et WhatsApp restent découplés de Hermes. La validation réelle du gateway reste nécessaire sur VPS.

## ADR-002 - Hermes comme cerveau

Contexte : l'assistant doit orchestrer les messages, le fournisseur IA et les outils disponibles.

Décision : utiliser Hermes Agent comme cerveau applicatif.

Conséquences : la logique principale reste dans Hermes. Les scripts du dépôt restent des aides d'exploitation.

## ADR-003 - MCP comme pont

Contexte : il faut relier OpenClaw et Hermes sans exposer trop d'outils.

Décision : utiliser MCP comme pont outillé.

Conséquences : les permissions MCP doivent être limitées et auditées.

## ADR-004 - Telegram avant WhatsApp

Contexte : Telegram est plus simple à tester pour un MVP.

Décision : livrer Telegram avant WhatsApp.

Conséquences : WhatsApp sera traité plus tard, avec attention aux sessions et QR codes.

## ADR-005 - OpenClaw/MCP non exposés publiquement

Contexte : les interfaces locales peuvent porter des actions sensibles.

Décision : ne pas exposer OpenClaw ni MCP publiquement.

Conséquences : utiliser `127.0.0.1`, UFW et éventuellement un tunnel SSH.

## ADR-006 - Boucle avec service systemd utilisateur

Contexte : le MVP doit redémarrer automatiquement sans service root.

Décision : utiliser `hermes-openclaw-loop.service` en unité systemd utilisateur.

Conséquences : `WorkingDirectory=%h/hermes-openclaw` et `ExecStart=%h/hermes-openclaw/scripts/loop.sh`.

## ADR-007 - Secrets hors Git

Contexte : le dépôt est public ou montrable à un recruteur.

Décision : aucun secret réel dans Git.

Conséquences : `.env.example` contient seulement des placeholders. `.env` reste local.

## ADR-008 - Sauvegarde simple puis chiffrée

Contexte : il faut sauvegarder sans complexifier le MVP.

Décision : commencer par une archive locale avec checksum, puis chiffrer avant stockage externe.

Conséquences : aucune archive brute ne doit sortir du VPS.

## ADR-009 - Docker Compose v2 seulement si nécessaire

Contexte : Docker peut être utile mais n'est pas obligatoire pour la première boucle.

Décision : utiliser `docker compose` seulement si plusieurs services persistants sont ajoutés.

Conséquences : pas de dépendance Compose forcée pour le MVP.

## ADR-010 - Monitoring, alerting et CI/CD plus tard

Contexte : le projet doit d'abord stabiliser le flux Telegram -> OpenClaw -> MCP -> Hermes.

Décision : reporter monitoring avancé, alerting et CI/CD.

Conséquences : les premières validations restent manuelles et locales.
