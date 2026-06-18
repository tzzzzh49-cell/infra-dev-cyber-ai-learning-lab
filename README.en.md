# Infra Dev Cyber AI Learning Lab

Local learning lab for Linux, networking, Docker, FastAPI, defensive diagnostics and DevSecOps practices.

The project is designed to stay reproducible, auditable and safe by default. The primary target is Ubuntu 26.04 LTS Server. Fedora Workstation 44 remains a secondary target, and Ubuntu 24.04.4 LTS Desktop is kept as a historical validated target.

## Current Scope

- FastAPI endpoints: `/`, `/health`, `/version`, `/diag`, `/diag/export/json`, `/diag/export/markdown`.
- Read-only network and system diagnostics.
- JSON and Markdown diagnostic exports in `outputs/reports`.
- Local-first Restic backup scripts.
- Docker Compose workflow bound to `127.0.0.1` by default.
- Python tests, Ruff, ShellCheck, Docker Compose validation, Bandit and Trivy in CI.
- Dependabot updates for Python dependencies, GitHub Actions and Docker.

## Security Defaults

Diagnostics are protected by default in every environment. The API never stores a plaintext diagnostic token. Configure `DIAG_ACCESS_TOKEN_HASH` or `DIAG_ACCESS_TOKEN_HASH_FILE` with a `sha256:<hash>` or `bcrypt:<hash>` value injected from a secrets manager such as Vault, AWS Secrets Manager, Docker secrets or a private mounted file.

Generate a token and hash:

```bash
python3 scripts/generate_diag_token.py --format sha256
```

Use the displayed token only on the client side, for example:

```bash
export DIAG_ACCESS_TOKEN='<DISPLAYED_TOKEN>'
export DIAG_ACCESS_TOKEN_HASH='<DISPLAYED_HASH>'
make up
make diag
```

`DIAG_PROTECTION_DISABLED=true` is only for explicit local development with `APP_ENV=local`, `lab`, `dev`, `development` or `test`. It is ignored outside local development environments.

## Quick Start

```bash
git clone https://github.com/tzzzzh49-cell/infra-dev-cyber-ai-learning-lab.git
cd infra-dev-cyber-ai-learning-lab
make check
python3 scripts/generate_diag_token.py --format sha256
export DIAG_ACCESS_TOKEN='<DISPLAYED_TOKEN>'
export DIAG_ACCESS_TOKEN_HASH='<DISPLAYED_HASH>'
make run
make health
make diag
make diag-json
make diag-md
make reports
make down
```

## Documentation

The main documentation remains in French:

- [README.md](README.md)
- [Architecture](docs/architecture.md)
- [Security](docs/securite.md)
- [Advanced network diagnostics](docs/diagnostic-reseau-v0.3.md)
- [VPS preparation](docs/vps/README.md)

Before opening a pull request, run:

```bash
make check
make test
make lint
make compose-config
```
