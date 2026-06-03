# Changelog

Toutes les modifications notables du projet seront documentées ici.

## Unreleased

### Added

- Documentation portfolio Hermes + OpenClaw Gateway.
- Guides installation, runbook, sécurité, sauvegarde, décisions et architecture.
- Scripts d'exemple pour boucle, healthcheck et sauvegarde.
- Unité systemd utilisateur `hermes-openclaw-loop.service`.
- Structure `docs/incidents/` et `screenshots/`.

### Changed

- README et roadmap réorientés vers l'assistant personnel auto-hébergé.
- `.gitignore` renforcé contre secrets, logs et sauvegardes.
- `.env.example` remplacé par des placeholders sûrs.

### Notes

- Le contenu legacy réseau/FastAPI reste conservé en attendant une migration prudente.
