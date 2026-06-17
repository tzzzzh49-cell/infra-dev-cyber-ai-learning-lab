# Project Security

> Languages: [Français](securite.md) | English

## Table Of Contents

- [Goal](#goal)
- [Main Principle](#main-principle)
- [Allowed Commands](#allowed-commands)
- [Forbidden Commands](#forbidden-commands)
- [HTTP Diagnostic Protection](#http-diagnostic-protection)
- [Timeouts And Retries](#timeouts-and-retries)
- [Logs](#logs)
- [Dependency Updates](#dependency-updates)
- [Secrets](#secrets)

## Goal

This project runs system and network observation commands. Security is therefore
a baseline requirement, not a later add-on.

The project intentionally starts in read-only mode.

## Main Principle

No destructive command must be automated at the current stage. The lab observes,
diagnoses, documents, explains and suggests next steps, but it does not modify
the host automatically.

## Allowed Commands

Allowed commands must be non-destructive, for example:

```bash
ip addr
ip route
ss -tulpn
df -h
free -h
uptime
hostnamectl
systemctl status
journalctl --no-pager
```

## Forbidden Commands

The application and scripts must not automate commands such as:

```bash
rm -rf
mkfs
dd
reboot
shutdown
ip route del
ip addr flush
firewall-cmd --remove
docker rm
docker system prune
sudo without justification
```

## HTTP Diagnostic Protection

Sensitive routes:

```text
/diag
/diag/export/json
/diag/export/markdown
```

Expected behavior:

- locally on `127.0.0.1`, diagnostics can remain open for learning;
- if `DIAG_ACCESS_TOKEN_SHA256` is set, the API compares the SHA-256 hash of the
  provided bearer or `X-Diag-Token` token;
- `DIAG_ACCESS_TOKEN` remains supported for local compatibility or reverse proxy
  injection, but must stay in a private untracked file;
- in `APP_ENV=vps`, a clear private token or hash is required;
- if VPS mode has no token configuration, diagnostic routes fail closed.

Use `scripts/generate_diag_token.py` to generate a client token and export only
`DIAG_ACCESS_TOKEN_SHA256` to the application.

## Timeouts And Retries

Diagnostic commands use `DIAG_COMMAND_TIMEOUT`, defaulting to `3` seconds. The
code caps this value to avoid blocking the API for too long.

`DIAG_COMMAND_RETRIES` defaults to `0` and is bounded. Extra attempts should only
be used for read-only idempotent commands in slow or transient environments.

## Logs

Application logs go to stdout/stderr. On a VPS, collect them with Docker
logging, a sidecar or an external agent. Do not persist local application log
files in the repository, because diagnostic logs can contain sensitive host
information.

## Dependency Updates

Suggested policy:

- review Python dependencies and the Docker base image monthly;
- react quickly to critical or publicly exploited vulnerabilities;
- run Bandit and Trivy locally before merge when available;
- never update dependencies automatically without changelog review and tests.

If Bandit or Trivy cannot run locally because their databases or binaries are
unavailable, document that in the Pull Request.

## Secrets

Never commit `.env` files with values, API keys, GitHub tokens, private SSH keys,
passwords, OpenClaw secrets, Restic passphrases or diagnostic client tokens.

Use example files with empty placeholders and private environment variables.
