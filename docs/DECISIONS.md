# Décisions d'architecture

Ce fichier suit un format ADR simple.
Chaque décision contient un contexte, une décision et des conséquences.

## ADR-001 - OpenClaw comme Gateway

Statut : accepté.

Contexte : le projet doit connecter des canaux de messagerie à un agent personnel.

Décision : utiliser OpenClaw comme Gateway pour Telegram puis WhatsApp.

Conséquences : OpenClaw concentre les intégrations de messagerie et reste non exposé publiquement.

## ADR-002 - Hermes comme cerveau

Statut : accepté.

Contexte : la logique de réponse doit rester séparée de la gateway.

Décision : utiliser Hermes Agent comme cerveau conversationnel.

Conséquences : le fournisseur IA et le modèle restent configurables hors Git.

## ADR-003 - MCP comme pont

Statut : accepté.

Contexte : Hermes doit utiliser OpenClaw sans couplage direct excessif.

Décision : utiliser MCP comme pont entre OpenClaw et Hermes.

Conséquences : les outils MCP doivent être limités au minimum nécessaire.

## ADR-004 - Telegram avant WhatsApp

Statut : accepté.

Contexte : le MVP doit être simple et testable.

Décision : livrer Telegram avant WhatsApp.

Conséquences : WhatsApp reste une étape ultérieure avec attention aux sessions et QR codes.

## ADR-005 - OpenClaw et MCP non exposés publiquement

Statut : accepté.

Contexte : les interfaces locales peuvent donner accès aux messages et outils.

Décision : garder OpenClaw et MCP sur `127.0.0.1` ou réseau privé.

Conséquences : utiliser un tunnel SSH si un accès distant temporaire est nécessaire.

## ADR-006 - Boucle avec service systemd utilisateur

Statut : accepté.

Contexte : le MVP doit tourner sans service root.

Décision : lancer `scripts/loop.sh` via `hermes-openclaw-loop.service` en unité utilisateur.

Conséquences : pas de `User=` dans l'unité et utilisation de `%h` pour le home.

## ADR-007 - Secrets hors Git

Statut : accepté.

Contexte : le dépôt est public ou partageable avec un recruteur.

Décision : stocker les secrets uniquement dans `.env` local et les répertoires privés.

Conséquences : `.env.example` ne contient que des placeholders.

## ADR-008 - Sauvegarde simple puis chiffrée

Statut : accepté.

Contexte : il faut une procédure compréhensible avant automatisation avancée.

Décision : créer une archive locale simple, puis chiffrer avant stockage externe.

Conséquences : les sauvegardes brutes restent sur le VPS et hors Git.

## ADR-009 - Docker Compose v2 seulement si nécessaire

Statut : accepté.

Contexte : le MVP peut fonctionner sans orchestration locale lourde.

Décision : utiliser `docker compose` seulement si plusieurs services persistants sont ajoutés.

Conséquences : pas de dépendance Docker obligatoire pour la première démonstration.

## ADR-010 - Monitoring, alerting et CI/CD plus tard

Statut : accepté.

Contexte : la priorité est la sécurité et le flux MVP.

Décision : reporter monitoring, alerting et CI/CD après validation Telegram, OpenClaw, Hermes et MCP.

Conséquences : la roadmap garde ces sujets visibles sans les mélanger au MVP.
