# Reproducibility On Ubuntu 26.04 LTS Server

> Languages: [Français](reproductibilite-ubuntu-26.04-server.md) | English

## Table Of Contents

- [Ubuntu Server Requirements](#ubuntu-server-requirements)
- [Validation Status](#validation-status)
- [Validation Flow](#1-clone-the-repository)
- [Local Restic Backups](#8-local-restic-backups)
- [Server Checklist](#server-checklist)
- [Security Notes](#security-notes)

This guide describes the expected reproducible flow on an Ubuntu 26.04 LTS
Server VM. Ubuntu Server becomes the priority target for v0.4.0 preparation.

Ubuntu 24.04.4 LTS Desktop remains a historical validated target, not the active
priority.

## Ubuntu Server Requirements

- Clean Ubuntu 26.04 LTS Server VM.
- Administrator user able to run the bootstrap script.
- Outbound network access to GitHub, Docker Hub and Docker repositories.
- Git installed or available through the bootstrap script.
- No real secret in the repository.

## Validation Status

Current status: **Server procedure prepared, real validation still to run**.

Only mark Ubuntu 26.04 LTS Server as validated after the validation journal
contains real command results from a clean VM:

```text
docs/validations/ubuntu-26.04-server-vm.md
```

## 1) Clone The Repository

```bash
git clone https://github.com/tzzzzh49-cell/infra-dev-cyber-ai-learning-lab.git
cd infra-dev-cyber-ai-learning-lab
git switch <validation-branch>
```

## 2) Bootstrap Ubuntu Server

```bash
make bootstrap-ubuntu
```

After Docker group changes, disconnect and reconnect if required.

## 3) Quick Check

```bash
make check
```

Expected result: important files exist, Python syntax is valid, pytest passes,
Ruff, ShellCheck and Docker Compose config pass, and no Git conflict marker is
present.

## 4) Full Validation

```bash
make check-full
```

This also runs the Docker build and the Ansible playbook in check mode. If it is
not run during real validation, document why in the validation journal.

## 5) Start The Application

```bash
make run
```

Expected result: the image builds, Compose starts the API and `/health` answers
on `http://127.0.0.1:8000` by default.

## 6) Endpoints To Check

```bash
make health
make version
make diag
```

`make diag` must return a structured read-only diagnostic with `metadata`,
`system`, `network`, `resources`, `docker` and `security`.

## 7) Diagnostic Exports

```bash
make diag-json
make diag-md
make diagnostic-local
make reports
```

Reports are written under `outputs/reports`. They may contain local system
information and must not be published without review.

## 8) Local Restic Backups

Create a private untracked file from `.env.backup.example`, then define:

```dotenv
RESTIC_REPOSITORY=outputs/backups/restic-local
RESTIC_PASSWORD_FILE=<ABSOLUTE_PATH_TO_PRIVATE_FILE>
RESTIC_EXCLUDE_FILE=backup/restic-excludes.txt
```

Run:

```bash
backup/init-local.sh
backup/backup-local.sh
restic snapshots
restic check
backup/restore-test-local.sh
```

Expected result: the local repository is initialized, a snapshot is created, the
repository is checked and a restore drill runs in `/tmp` without overwriting the
working tree.

## Server Checklist

- [ ] repository cloned from GitHub;
- [ ] dedicated validation branch selected;
- [ ] `make bootstrap-ubuntu` completed;
- [ ] Docker group reconnect completed if needed;
- [ ] `docker --version` works without `sudo`;
- [ ] `docker compose version` works without `sudo`;
- [ ] `make check` passed;
- [ ] `make test` passed;
- [ ] `make lint` passed;
- [ ] `make compose-config` passed;
- [ ] `make check-full` passed or was explicitly documented as skipped;
- [ ] API starts on `127.0.0.1`;
- [ ] `/health`, `/version` and `/diag` checked;
- [ ] JSON and Markdown exports created;
- [ ] Restic init, backup, snapshots, check and restore drill tested;
- [ ] `make down` stops the application cleanly.

## Security Notes

- Diagnostics remain strictly read-only.
- Do not add real secrets to examples, scripts, reports or commits.
- Do not expose `/diag` or exports publicly without authentication and HTTPS
  reverse proxy protection.
- Prefer `DIAG_ACCESS_TOKEN_SHA256` over storing a clear application token.
- `DIAG_COMMAND_TIMEOUT` defaults to `3` seconds; only raise it for a documented
  slow environment.
- Protected API call examples are in `docs/api-examples.md`.
