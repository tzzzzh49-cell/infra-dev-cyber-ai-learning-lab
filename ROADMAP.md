# Roadmap

## Phase 1 - MVP Telegram

Objectif : valider le flux minimal Telegram -> OpenClaw -> MCP -> Hermes -> réponse.

- [x] Documenter l'architecture cible.
- [x] Ajouter `.env.example` sans secret.
- [x] Préparer la boucle `scripts/loop.sh`.
- [ ] Créer un bot Telegram réel hors Git.
- [ ] Valider OpenClaw Gateway avec Telegram sur VPS.
- [ ] Vérifier que les logs ne contiennent pas de messages privés.

## Phase 2 - Validation MCP

Objectif : sécuriser le pont entre OpenClaw et Hermes.

- [x] Décrire les limites de confiance.
- [x] Documenter les outils MCP à limiter.
- [ ] Valider la configuration officielle MCP selon les versions installées.
- [ ] Tester un message entrant de bout en bout.
- [ ] Documenter les erreurs courantes.

## Phase 3 - systemd utilisateur

Objectif : maintenir l'assistant actif sans session SSH.

- [x] Ajouter `systemd/hermes-openclaw-loop.service`.
- [x] Documenter `systemctl --user`.
- [ ] Tester `enable --now` sur VPS.
- [ ] Tester `loginctl enable-linger` sur VPS.
- [ ] Vérifier le redémarrage automatique.

## Phase 4 - Sauvegardes

Objectif : protéger la configuration locale.

- [x] Ajouter `scripts/backup-example.sh`.
- [x] Documenter checksum, permissions et chiffrement.
- [ ] Tester une archive locale réelle.
- [ ] Tester une restauration dans un dossier temporaire.
- [ ] Valider une sauvegarde chiffrée hors VPS.

## Phase 5 - Monitoring

Objectif : détecter les pannes sans exposer les secrets.

- [ ] Ajouter un healthcheck régulier.
- [ ] Ajouter une alerte simple en cas d'arrêt du service.
- [ ] Ajouter une rotation de logs si nécessaire.

## Phase 6 - WhatsApp plus tard

Objectif : ajouter WhatsApp après stabilisation Telegram.

- [ ] Étudier la gestion de session.
- [ ] Définir une règle stricte pour QR codes.
- [ ] Tester sans publier de capture brute.

## Phase 7 - CI/CD plus tard

Objectif : automatiser les validations sûres.

- [ ] Ajouter une GitHub Action pour `bash -n`.
- [ ] Ajouter `shellcheck` si disponible.
- [ ] Ajouter `markdownlint` si la configuration est prête.
- [ ] Ne jamais exécuter de commandes VPS depuis CI.

## Phase 8 - Sécurité avancée plus tard

Objectif : renforcer la production.

- [ ] Gestionnaire de secrets.
- [ ] Monitoring de coûts IA.
- [ ] Alerting de sécurité.
- [ ] Revue d'allowlists MCP.
- [ ] Procédure de révocation testée.
