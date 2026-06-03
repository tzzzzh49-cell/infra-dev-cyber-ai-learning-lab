# Décisions d'architecture

Format ADR simplifié : contexte, décision, conséquences.

## ADR-001 - OpenClaw comme Gateway

Contexte : l'assistant doit recevoir et envoyer des messages via des canaux de messagerie.

Décision : utiliser OpenClaw comme gateway entre Telegram/WhatsApp et le reste du système.

Conséquences : OpenClaw concentre les intégrations messagerie. Il doit rester local et protégé.

## ADR-002 - Hermes comme cerveau

Contexte : la logique de réponse doit rester séparée de la gateway.

Décision : utiliser Hermes comme agent principal pour lire le contexte autorisé, appeler le fournisseur IA et rédiger une réponse courte.

Conséquences : les fournisseurs et modèles peuvent évoluer sans changer la gateway.

## ADR-003 - MCP comme pont

Contexte : il faut relier OpenClaw et Hermes avec une frontière claire.

Décision : utiliser MCP comme pont contrôlé.

Conséquences : les outils exposés doivent être limités et audités.

## ADR-004 - Telegram avant WhatsApp

Contexte : WhatsApp ajoute souvent de la complexité, des sessions et des QR codes sensibles.

Décision : livrer le MVP avec Telegram, puis ajouter WhatsApp plus tard.

Conséquences : moins de risque au démarrage, meilleure lisibilité pour un portfolio.

## ADR-005 - OpenClaw et MCP non exposés publiquement

Contexte : la gateway et MCP peuvent donner accès à des messages et actions sensibles.

Décision : les garder en local sur le VPS ou derrière un tunnel SSH.

Conséquences : le firewall doit bloquer tout accès public aux ports internes.

## ADR-006 - Boucle avec service systemd utilisateur

Contexte : l'assistant doit tourner sans session SSH active.

Décision : lancer `scripts/loop.sh` via `hermes-openclaw-loop.service` en unité utilisateur.

Conséquences : pas de service root, redémarrage automatique, gestion avec `systemctl --user`.

## ADR-007 - Secrets hors Git

Contexte : tokens, clés IA et sessions sont critiques.

Décision : aucun secret réel dans Git. `.env.example` contient seulement des placeholders.

Conséquences : `.gitignore` doit bloquer les secrets et sauvegardes.

## ADR-008 - Sauvegarde simple puis chiffrée

Contexte : il faut pouvoir restaurer sans complexifier le MVP.

Décision : générer d'abord une archive locale et un checksum, puis chiffrer avant stockage externe.

Conséquences : le stockage hors VPS est interdit sans chiffrement.

## ADR-009 - Docker Compose v2 seulement si nécessaire

Contexte : le MVP peut fonctionner avec des commandes locales et systemd.

Décision : Docker Compose v2 reste optionnel et sera utilisé si plusieurs services persistants sont ajoutés.

Conséquences : documentation harmonisée sur `docker compose`, pas `docker-compose`.

## ADR-010 - Monitoring, alerting et CI/CD plus tard

Contexte : la priorité est la documentation sûre et le MVP Telegram.

Décision : reporter monitoring, alerting et CI/CD après validation du flux réel.

Conséquences : la roadmap garde ces sujets comme étapes futures.
