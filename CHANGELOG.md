# Changelog

Toutes les modifications notables de ce projet seront documentées ici.

## Unreleased

### Added

- Documentation portfolio pour Hermes + OpenClaw Gateway.
- Guides d'installation, runbook, sécurité, sauvegarde, décisions et
  architecture.
- Scripts exemples pour boucle, healthcheck et sauvegarde locale.
- Unité systemd utilisateur `hermes-openclaw-loop.service`.
- Dossiers réservés aux incidents futurs et captures floutées.

### Changed

- Roadmap recentrée sur MVP Telegram, MCP, systemd, sauvegardes et sécurité.
- `.env.example` limité à des placeholders sans secret réel.
- `.gitignore` renforcé contre secrets, logs, bases et archives.

### Notes

- Les anciens éléments de lab réseau/FastAPI sont conservés pour migration
  prudente dans une PR dédiée.
