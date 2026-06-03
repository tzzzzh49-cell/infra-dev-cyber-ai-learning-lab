# Roadmap

## Phase 1 - MVP Telegram

Objectif : recevoir un message Telegram via OpenClaw et renvoyer une réponse
courte générée par Hermes.

- [x] Documenter l'architecture cible.
- [x] Préparer `.env.example` sans secret.
- [x] Préparer la boucle `scripts/loop.sh`.
- [ ] Installer OpenClaw sur VPS Ubuntu 24.04.
- [ ] Installer Hermes sur VPS Ubuntu 24.04.
- [ ] Configurer un token Telegram réel dans `.env` local uniquement.
- [ ] Valider un échange Telegram de bout en bout.

## Phase 2 - Validation MCP

Objectif : relier proprement OpenClaw et Hermes avec une surface minimale.

- [x] Documenter MCP comme pont local.
- [ ] Lister les outils MCP réellement nécessaires.
- [ ] Bloquer les outils dangereux.
- [ ] Tester lecture d'événement et envoi de réponse.
- [ ] Documenter les erreurs courantes.

## Phase 3 - Service systemd utilisateur

Objectif : faire tourner la boucle sans service root.

- [x] Ajouter `systemd/hermes-openclaw-loop.service`.
- [x] Documenter les commandes `systemctl --user`.
- [ ] Installer l'unité sur VPS.
- [ ] Valider `Restart=always`.
- [ ] Vérifier les logs sans messages privés.

## Phase 4 - Sauvegardes

Objectif : restaurer la configuration sans fuite de secrets.

- [x] Ajouter `scripts/backup-example.sh`.
- [x] Documenter checksum, permissions et chiffrement.
- [ ] Tester une sauvegarde locale.
- [ ] Chiffrer avec GPG ou age.
- [ ] Tester une restauration sur environnement de test.

## Phase 5 - Monitoring

Objectif : détecter les pannes sans exposer les données privées.

- [ ] Ajouter métriques légères.
- [ ] Ajouter alerting simple.
- [ ] Documenter seuils CPU, RAM et disque.
- [ ] Éviter les messages privés dans les alertes.

## Phase 6 - WhatsApp plus tard

Objectif : ajouter WhatsApp après sécurisation du MVP.

- [ ] Étudier les contraintes de session.
- [ ] Protéger QR codes et sessions.
- [ ] Tester sur compte dédié.
- [ ] Documenter révocation et rotation.

## Phase 7 - CI/CD plus tard

Objectif : automatiser seulement les validations sûres.

- [ ] Ajouter lint Markdown.
- [ ] Ajouter ShellCheck.
- [ ] Ajouter grep de secrets.
- [ ] Éviter tout test qui contacte un VPS ou un fournisseur IA réel.

## Phase 8 - Sécurité avancée plus tard

Objectif : réduire encore la surface d'attaque.

- [ ] Durcissement systemd.
- [ ] Allowlist MCP stricte.
- [ ] Rotation périodique des tokens.
- [ ] Sauvegardes chiffrées automatisées.
- [ ] Revue de menace complète.
