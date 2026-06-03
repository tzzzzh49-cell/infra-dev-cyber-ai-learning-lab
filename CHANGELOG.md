# Changelog

Toutes les évolutions notables du projet seront documentées ici.

## Unreleased

### Added

- Documentation portfolio pour Hermes + OpenClaw Gateway.
- Guides d'installation, runbook, sécurité, sauvegarde et décisions ADR.
- Scripts d'exemple pour boucle, healthcheck et sauvegarde.
- Unité systemd utilisateur `hermes-openclaw-loop.service`.
- Dossiers `docs/incidents/` et `screenshots/` avec `.gitkeep`.

### Changed

- Roadmap réorientée vers MVP Telegram, MCP, systemd et sauvegardes.
- `.gitignore` renforcé contre secrets, logs, sauvegardes et sessions locales.
- `.env.example` remplacé par des placeholders Hermes/OpenClaw.

### Security

- Ajout de règles explicites pour secrets, captures floutées et révocation de tokens.
