# Project Architecture

> Languages: [Français](architecture.md) | English

## Table Of Contents

- [Goal](#goal)
- [Current Architecture](#current-architecture)
- [Components](#components)
- [Docker And Compose Choices](#docker-and-compose-choices)
- [Prepared Persistence](#prepared-persistence)
- [Planned Evolution](#planned-evolution)
- [Architecture Principles](#architecture-principles)

## Goal

This project is a learning lab for Linux, networking, Docker, FastAPI,
automation and defensive cybersecurity.

The application is built progressively to:

- expose a minimal API;
- run read-only system and network diagnostics;
- produce technical reports;
- prepare a later VPS deployment;
- prepare a future OpenAI API integration;
- prepare controlled OpenClaw usage.

## Current Architecture

```text
User
   ↓
Makefile
   ↓
Docker Compose
   ↓
FastAPI application
   ↓
app/main.py
   ↓
app/diagnostics.py
   ↓
Endpoints: /health, /version, /diag, /diag/export/json, /diag/export/markdown
   ↓
Local reports: outputs/reports/*.json and outputs/reports/*.md
```

## Components

### FastAPI

FastAPI exposes a small API used to verify service health and run controlled
diagnostics.

Current endpoints:

- `/health`: checks that the application responds;
- `/version`: returns the application version;
- `/diag`: returns a structured read-only system/network diagnostic;
- `/diag/export/json`: writes a local JSON report;
- `/diag/export/markdown`: writes a local Markdown report.

### `app/diagnostics.py`

The diagnostics module centralizes read-only collection. It uses the Python
standard library, runs commands without `shell=True`, applies short bounded
timeouts and handles missing commands without uncontrolled exceptions.

It collects system information, interfaces, routes, DNS, open ports, disk,
memory and Docker state through read-only commands.

### Docker Compose

Docker Compose provides a reproducible runtime and prepares the future VPS flow.

### Scripts

Scripts automate bootstrap, local diagnostics and validation tasks. They must
remain readable and avoid destructive host changes.

## Docker And Compose Choices

The application image uses a multi-stage build:

- the `builder` stage installs pinned runtime dependencies from
  `app/requirements.txt` into a virtual environment;
- the `runtime` stage copies that environment, the app code and selected
  configuration files into separate directories;
- the code stays root-owned and the container runs as non-root user `10001:10001`.

The non-root user reduces the impact of an application flaw. Compose repeats
the same user setting, makes the root filesystem read-only, drops all Linux
capabilities and enables `no-new-privileges`.

The only writable mounts are `./outputs/reports` and `./outputs/logs`.
`outputs/raw`, `outputs/backups`, the full repository, `.env` files and local
secrets are not mounted into the container.

`restart: unless-stopped` models a VPS-friendly runtime: the service comes back
after a Docker restart, while explicit operator shutdown remains respected.

Application logs go to stdout/stderr. On a VPS, Docker logging, a sidecar or an
external agent should collect them without keeping sensitive local log files in
the repository.

## Prepared Persistence

Persistence is not active in v0.3.x. Compose prepares an inactive
`future-persistence` profile with Postgres and a `postgres_data` volume.

Before real use, the project needs a reviewed PostgreSQL dependency, migrations
such as Alembic, retention rules and a dedicated or external storage strategy
for reviewed AI reports. The `ai_reports` volume is reserved for that future
work.

## CORS Future

CORS middleware is not enabled today. If a local frontend or a separate AI
service consumes the API later, allowed origins must be enumerated explicitly,
for example through `CORS_ALLOWED_ORIGINS`. Wildcards must not be used in VPS
mode.

## Planned Evolution

1. Ubuntu 26.04 LTS Server local validation.
2. Quality checks with tests, linting and CI.
3. VPS deployment with SSH hardening, firewall and HTTPS.
4. OpenAI API usage for report summaries.
5. Controlled OpenClaw usage with a strict allowlist.

## Architecture Principles

- start simple;
- document every decision;
- prioritize reproducibility;
- limit privileges;
- never automate destructive commands;
- add AI features gradually and keep human validation.
