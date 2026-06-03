# Roadmap Hermes + OpenClaw Gateway

## Phase 1 - MVP Telegram

- [x] Documenter l'architecture cible.
- [x] Préparer `.env.example` sans secrets.
- [x] Ajouter une boucle d'orchestration d'exemple.
- [ ] Installer OpenClaw sur VPS Ubuntu 24.04.
- [ ] Installer Hermes sur VPS Ubuntu 24.04.
- [ ] Configurer Telegram avec token réel hors Git.
- [ ] Envoyer un message de test non sensible.

## Phase 2 - Validation MCP

- [ ] Déclarer le pont OpenClaw vers Hermes.
- [ ] Limiter les outils MCP.
- [ ] Tester lecture d'événement.
- [ ] Tester envoi de réponse.
- [ ] Documenter les erreurs observées.

## Phase 3 - systemd utilisateur

- [x] Fournir `systemd/hermes-openclaw-loop.service`.
- [ ] Installer l'unité sur le VPS.
- [ ] Valider `systemctl --user status`.
- [ ] Valider les logs `journalctl --user`.
- [ ] Activer le linger si nécessaire.

## Phase 4 - Sauvegardes

- [x] Documenter la stratégie de sauvegarde.
- [x] Ajouter `scripts/backup-example.sh`.
- [ ] Tester une archive locale.
- [ ] Tester le checksum.
- [ ] Tester le chiffrement GPG ou age.
- [ ] Tester une restauration dans un dossier temporaire.

## Phase 5 - Monitoring

- [ ] Ajouter une vérification périodique.
- [ ] Ajouter une alerte simple en cas de service arrêté.
- [ ] Suivre disque, mémoire et erreurs récurrentes.

## Phase 6 - WhatsApp plus tard

- [ ] Étudier le support OpenClaw WhatsApp.
- [ ] Protéger les sessions et QR codes.
- [ ] Tester sur un environnement séparé.
- [ ] Documenter les limites et risques.

## Phase 7 - CI/CD plus tard

- [ ] Ajouter lint Markdown.
- [ ] Ajouter ShellCheck en CI.
- [ ] Ajouter validation des scripts.
- [ ] Ajouter scan basique de secrets.

## Phase 8 - Sécurité avancée plus tard

- [ ] Durcir l'unité systemd si compatible.
- [ ] Ajouter rotation de secrets.
- [ ] Ajouter sauvegardes chiffrées automatisées.
- [ ] Ajouter revue MCP régulière.

## Migration prudente du contenu legacy

Le dépôt contient encore un ancien lab réseau/FastAPI. Il est conservé pour éviter une suppression brutale. À terme, déplacer les éléments utiles vers `docs/legacy/` ou supprimer après revue explicite.
