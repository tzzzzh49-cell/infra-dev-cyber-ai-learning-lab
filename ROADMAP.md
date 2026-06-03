# Roadmap

## Phase 1 - MVP Telegram

- [x] Documenter l'architecture Hermes + OpenClaw Gateway.
- [x] Ajouter `.env.example` sans secret.
- [x] Préparer les scripts locaux.
- [ ] Installer OpenClaw sur VPS Ubuntu 24.04.
- [ ] Installer Hermes sur VPS Ubuntu 24.04.
- [ ] Valider un message Telegram de bout en bout.

## Phase 2 - Validation MCP

- [ ] Lister les outils MCP réellement disponibles.
- [ ] Limiter les outils au strict nécessaire.
- [ ] Tester lecture conversation et envoi réponse.
- [ ] Documenter les commandes exactes selon versions officielles.

## Phase 3 - systemd utilisateur

- [x] Ajouter `systemd/hermes-openclaw-loop.service`.
- [ ] Installer l'unité sur le VPS.
- [ ] Valider `systemctl --user`.
- [ ] Valider `loginctl enable-linger`.

## Phase 4 - Sauvegardes

- [x] Ajouter un script de sauvegarde exemple.
- [x] Documenter checksum, chmod et chiffrement.
- [ ] Tester une restauration dans un dossier temporaire.
- [ ] Ajouter une routine hebdomadaire.

## Phase 5 - Monitoring

- [ ] Ajouter une vérification périodique de santé.
- [ ] Ajouter une alerte en cas de service arrêté.
- [ ] Suivre disque, mémoire et erreurs répétées.

## Phase 6 - WhatsApp plus tard

- [ ] Évaluer le connecteur WhatsApp OpenClaw.
- [ ] Protéger les sessions et QR codes.
- [ ] Tester sans publier de capture brute.

## Phase 7 - CI/CD plus tard

- [ ] Ajouter lint Markdown.
- [ ] Ajouter lint shell.
- [ ] Ajouter vérification de secrets en CI.
- [ ] Publier automatiquement la documentation si utile.

## Phase 8 - Sécurité avancée plus tard

- [ ] Durcir systemd.
- [ ] Auditer les permissions MCP.
- [ ] Chiffrer toutes les sauvegardes hors VPS.
- [ ] Ajouter rotation et révocation documentées.
