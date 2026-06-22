"""Read-only diagnostic helpers for the local learning lab."""

import json
import os
import platform
import socket
import subprocess
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.logging_config import configure_logging

SCHEMA_VERSION = "0.3.0"
DEFAULT_REPORT_DIR = "outputs/reports"
DEFAULT_COMMAND_TIMEOUT = 3
MAX_COMMAND_TIMEOUT = 30.0
DIAG_COMMAND_TIMEOUT_ENV = "DIAG_COMMAND_TIMEOUT"
DIAG_COMMAND_RETRIES_ENV = "DIAG_COMMAND_RETRIES"
DEFAULT_COMMAND_RETRIES = 0
MAX_COMMAND_RETRIES = 2
MAX_REPORT_FILES_PER_FORMAT = 20
ALLOWED_DIAGNOSTIC_COMMANDS: tuple[tuple[str, ...], ...] = (
    ("ip", "-j", "addr"),
    ("ip", "-j", "route"),
    ("resolvectl", "dns"),
    ("resolvectl", "status"),
    ("systemd-resolve", "--status"),
    ("nmcli", "dev", "show"),
    ("ss", "-tulpn"),
    ("df", "-h"),
    ("free", "-h"),
    ("docker", "ps", "--format", "{{json .}}"),
)
DNS_RESOLVER_COMMANDS: tuple[tuple[str, ...], ...] = (
    ("resolvectl", "dns"),
    ("resolvectl", "status"),
    ("systemd-resolve", "--status"),
    ("nmcli", "dev", "show"),
)

logger = configure_logging(__name__)


def utc_timestamp() -> str:
    """Return an ISO-8601 UTC timestamp."""
    return datetime.now(UTC).isoformat()


def filename_timestamp() -> str:
    """Return a filesystem-friendly UTC timestamp."""
    return datetime.now(UTC).strftime("%Y-%m-%d-%H%M%S-%f")


def normalize_command_output(value: str | bytes | None) -> str:
    """Return command output as text regardless of subprocess exception details."""
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return value


def parse_positive_float(value: str, default: float, maximum: float) -> float:
    """Parse a bounded positive float from an environment value."""
    try:
        parsed = float(value)
    except ValueError:
        return default

    if parsed <= 0:
        return default
    return min(parsed, maximum)


def parse_bounded_int(value: str, default: int, maximum: int) -> int:
    """Parse a bounded non-negative integer from an environment value."""
    try:
        parsed = int(value)
    except ValueError:
        return default

    if parsed < 0:
        return default
    return min(parsed, maximum)


def get_default_command_timeout() -> float:
    """Return the diagnostic command timeout from the environment."""
    configured = os.environ.get(DIAG_COMMAND_TIMEOUT_ENV, "").strip()
    if not configured:
        return DEFAULT_COMMAND_TIMEOUT
    return parse_positive_float(
        configured,
        default=DEFAULT_COMMAND_TIMEOUT,
        maximum=MAX_COMMAND_TIMEOUT,
    )


def resolve_command_timeout(timeout: float | None) -> float:
    """Return an explicit timeout or the environment-backed default."""
    if timeout is not None:
        return timeout
    return get_default_command_timeout()


def get_default_command_retries() -> int:
    """Return the bounded diagnostic retry count from the environment."""
    configured = os.environ.get(DIAG_COMMAND_RETRIES_ENV, "").strip()
    if not configured:
        return DEFAULT_COMMAND_RETRIES
    return parse_bounded_int(
        configured,
        default=DEFAULT_COMMAND_RETRIES,
        maximum=MAX_COMMAND_RETRIES,
    )


def resolve_command_retries(retries: int | None) -> int:
    """Return an explicit retry count or the environment-backed default."""
    if retries is not None:
        return max(0, min(retries, MAX_COMMAND_RETRIES))
    return get_default_command_retries()


def base_command_result(command: list[str], timeout: float) -> dict[str, Any]:
    """Create the stable command result structure used by diagnostics."""
    return {
        "command": command,
        "available": False,
        "returncode": None,
        "stdout": "",
        "stderr": "",
        "timed_out": False,
        "timeout_seconds": timeout,
        "duration_seconds": 0.0,
        "error_type": "",
        "attempts": 0,
    }


def finish_command_result(
    result: dict[str, Any],
    started_at: float,
) -> dict[str, Any]:
    """Record command duration before returning a command result."""
    result["duration_seconds"] = round(time.monotonic() - started_at, 6)
    return result


def run_read_only_command(
    command: list[str],
    timeout: float | None = None,
    retries: int | None = None,
) -> dict[str, Any]:
    """Run a short read-only command without a shell and return a stable result."""
    started_at = time.monotonic()
    command_timeout = resolve_command_timeout(timeout)
    command_retries = resolve_command_retries(retries)
    result = base_command_result(command, command_timeout)

    if not command:
        result["error_type"] = "empty_command"
        result["stderr"] = "No command provided."
        logger.error("Refusing to run an empty diagnostic command.")
        return finish_command_result(result, started_at)

    logger.info("Running read-only diagnostic command: %s", " ".join(command))

    completed: subprocess.CompletedProcess[str] | None = None
    for attempt in range(command_retries + 1):
        result["attempts"] = attempt + 1
        try:
            completed = subprocess.run(  # nosec B603: command list comes from an allowlist.
                command,
                capture_output=True,
                text=True,
                check=False,
                timeout=command_timeout,
            )
        except FileNotFoundError as exc:
            result["error_type"] = "command_not_found"
            result["stderr"] = str(exc)
            logger.warning("Diagnostic command not found: %s", command[0])
            return finish_command_result(result, started_at)
        except subprocess.TimeoutExpired as exc:
            result["available"] = True
            result["timed_out"] = True
            result["error_type"] = "timeout"
            result["stdout"] = normalize_command_output(exc.stdout)
            result["stderr"] = normalize_command_output(exc.stderr) or (
                f"Command timed out after {command_timeout:g}s"
            )
            logger.error(
                "Diagnostic command timed out after %ss: %s",
                command_timeout,
                command,
            )
            if attempt < command_retries:
                continue
            return finish_command_result(result, started_at)
        except OSError as exc:
            result["error_type"] = "os_error"
            result["stderr"] = str(exc)
            logger.error("Diagnostic command failed before execution: %s", exc)
            return finish_command_result(result, started_at)
        else:
            break

    result["available"] = True
    result["returncode"] = completed.returncode if completed else None
    result["stdout"] = completed.stdout if completed else ""
    result["stderr"] = completed.stderr if completed else ""
    result["timed_out"] = False
    if completed.returncode != 0:
        result["error_type"] = "non_zero_exit"
        logger.warning(
            "Diagnostic command returned %s: %s",
            completed.returncode,
            command,
        )
    else:
        logger.info("Diagnostic command completed: %s", command)
    return finish_command_result(result, started_at)


def allowed_diagnostic_command(command: list[str]) -> bool:
    """Return true when a command belongs to the diagnostic allowlist."""
    return tuple(command) in ALLOWED_DIAGNOSTIC_COMMANDS


def run_diagnostic_command(
    command: list[str],
    timeout: float | None = None,
    retries: int | None = None,
) -> dict[str, Any]:
    """Run an allowlisted read-only diagnostic command."""
    command_timeout = resolve_command_timeout(timeout)
    result: dict[str, Any] = {
        **base_command_result(command, command_timeout),
    }

    if not allowed_diagnostic_command(command):
        result["error_type"] = "command_not_allowed"
        result["stderr"] = "Command is not in the diagnostic allowlist."
        logger.error("Blocked non-allowlisted diagnostic command: %s", command)
        return result
    return run_read_only_command(command, timeout=command_timeout, retries=retries)


def collect_system_info() -> dict[str, str]:
    """Collect portable system metadata using the Python standard library."""
    return {
        "hostname": socket.gethostname(),
        "platform": platform.system(),
        "platform_version": platform.version(),
        "python_version": platform.python_version(),
    }


def parse_json_output(
    command_result: dict[str, Any],
) -> list[Any] | dict[str, Any] | None:
    """Parse a JSON command output when possible."""
    if not command_result.get("stdout"):
        return None

    try:
        parsed = json.loads(str(command_result["stdout"]))
    except json.JSONDecodeError:
        return None
    return parsed


def parse_json_lines(command_result: dict[str, Any]) -> list[Any]:
    """Parse newline-delimited JSON objects, preserving invalid lines as raw data."""
    items: list[Any] = []
    stdout = str(command_result.get("stdout", ""))

    for line in stdout.splitlines():
        if not line.strip():
            continue
        try:
            items.append(json.loads(line))
        except json.JSONDecodeError:
            items.append({"raw": line})

    return items


def read_resolv_conf(path: str = "/etc/resolv.conf") -> dict[str, Any]:
    """Read /etc/resolv.conf without modifying it."""
    resolv_path = Path(path)
    data: dict[str, Any] = {
        "path": path,
        "available": False,
        "content": "",
        "nameservers": [],
        "search": [],
        "options": [],
        "error": "",
    }

    try:
        content = resolv_path.read_text(encoding="utf-8", errors="replace")
    except FileNotFoundError as exc:
        data["error"] = str(exc)
        return data
    except OSError as exc:
        data["error"] = str(exc)
        return data

    data["available"] = True
    data["content"] = content

    for line in content.splitlines():
        clean_line = line.strip()
        if not clean_line or clean_line.startswith("#"):
            continue
        parts = clean_line.split()
        key = parts[0]
        values = parts[1:]
        if key == "nameserver":
            data["nameservers"].extend(values)
        elif key == "search":
            data["search"].extend(values)
        elif key == "options":
            data["options"].extend(values)

    return data


def collect_dns_resolver_commands(
    timeout: float | None = None,
) -> dict[str, Any]:
    """Collect DNS resolver details using resolvectl and portable fallbacks."""
    command_timeout = resolve_command_timeout(timeout)
    attempts: list[dict[str, Any]] = []
    selected: dict[str, Any] | None = None

    for command in DNS_RESOLVER_COMMANDS:
        result = run_diagnostic_command(list(command), timeout=command_timeout)
        attempts.append(result)
        if selected is None and result["available"] and result["returncode"] == 0:
            selected = result
            break

    return {
        "selected": selected,
        "attempts": attempts,
        "fallbacks": [list(command) for command in DNS_RESOLVER_COMMANDS[1:]],
    }


def command_with_parsed_json(
    command: list[str],
    timeout: float | None = None,
) -> dict[str, Any]:
    """Run a command and attach parsed JSON output when valid."""
    result = run_diagnostic_command(command, timeout=timeout)
    result["parsed"] = parse_json_output(result)
    return result


def collect_network_diagnostic(
    resolv_conf_path: str = "/etc/resolv.conf",
    command_timeout: float | None = None,
) -> dict[str, Any]:
    """Collect an advanced read-only system and network diagnostic."""
    effective_timeout = resolve_command_timeout(command_timeout)
    interfaces = command_with_parsed_json(
        ["ip", "-j", "addr"],
        timeout=effective_timeout,
    )
    routes = command_with_parsed_json(["ip", "-j", "route"], timeout=effective_timeout)
    ports = run_diagnostic_command(["ss", "-tulpn"], timeout=effective_timeout)
    disk = run_diagnostic_command(["df", "-h"], timeout=effective_timeout)
    memory = run_diagnostic_command(["free", "-h"], timeout=effective_timeout)
    docker = run_diagnostic_command(
        ["docker", "ps", "--format", "{{json .}}"], timeout=effective_timeout
    )
    docker["parsed"] = parse_json_lines(docker)
    resolver_commands = collect_dns_resolver_commands(timeout=effective_timeout)

    return {
        "metadata": {
            "schema_version": SCHEMA_VERSION,
            "generated_at_utc": utc_timestamp(),
            "mode": "read-only",
            "command_timeout_seconds": effective_timeout,
        },
        "system": collect_system_info(),
        "network": {
            "interfaces": interfaces,
            "routes": routes,
            "dns": {
                "resolv_conf": read_resolv_conf(resolv_conf_path),
                "resolver_commands": resolver_commands,
            },
            "ports": ports,
        },
        "resources": {
            "disk": disk,
            "memory": memory,
        },
        "docker": docker,
        "security": {
            "read_only": True,
            "destructive_commands_used": False,
            "allowed_commands": [
                list(command) for command in ALLOWED_DIAGNOSTIC_COMMANDS
            ],
        },
    }


def ensure_report_dir(output_dir: str | Path) -> Path:
    """Create and return the report directory path."""
    report_dir = Path(output_dir)
    report_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
    report_dir.chmod(0o700)
    logger.info("Diagnostic report directory ready: %s", report_dir)
    return report_dir


def prune_old_reports(
    report_dir: Path,
    suffix: str,
    keep: int = MAX_REPORT_FILES_PER_FORMAT,
) -> None:
    """Keep only the newest diagnostic reports for one file format."""
    reports = sorted(report_dir.glob(f"diagnostic-network-*{suffix}"))
    for report_path in reports[:-keep]:
        report_path.unlink()
        logger.info("Removed expired diagnostic report: %s", report_path)


def write_json_report(
    report: dict[str, Any],
    output_dir: str | Path = DEFAULT_REPORT_DIR,
) -> str:
    """Write a timestamped JSON diagnostic report and return its path."""
    report_dir = ensure_report_dir(output_dir)
    report_path = report_dir / f"diagnostic-network-{filename_timestamp()}.json"
    report_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    report_path.chmod(0o600)
    prune_old_reports(report_dir, ".json")
    logger.info("Wrote JSON diagnostic report: %s", report_path)
    return str(report_path)


def command_block(section: dict[str, Any]) -> str:
    """Render a command result as a Markdown code block."""
    command = " ".join(section.get("command", []))
    stdout = str(section.get("stdout", "")).strip()
    stderr = str(section.get("stderr", "")).strip()
    returncode = section.get("returncode")
    available = section.get("available")
    timed_out = section.get("timed_out")

    lines = [
        f"- Commande : `{command}`",
        f"- Disponible : `{available}`",
        f"- Code retour : `{returncode}`",
        f"- Timeout : `{timed_out}`",
        "",
        "```text",
        stdout or "(aucune sortie standard)",
        "```",
    ]
    if stderr:
        lines.extend(["", "Erreur standard :", "", "```text", stderr, "```"])
    return "\n".join(lines)


def resolver_commands_block(section: dict[str, Any]) -> str:
    """Render DNS resolver command attempts as Markdown."""
    selected = section.get("selected")
    attempts = section.get("attempts", [])
    lines = [
        "Commandes candidates :",
        "",
    ]

    for attempt in attempts:
        command = " ".join(attempt.get("command", []))
        available = attempt.get("available")
        returncode = attempt.get("returncode")
        error_type = attempt.get("error_type") or "aucune"
        lines.append(
            f"- `{command}` : disponible=`{available}`, "
            f"code=`{returncode}`, erreur=`{error_type}`"
        )

    lines.extend(["", "Commande retenue :", ""])
    if selected:
        lines.append(command_block(selected))
    else:
        lines.append("Aucune commande DNS alternative n'a répondu correctement.")
    return "\n".join(lines)


def write_markdown_report(
    report: dict[str, Any],
    output_dir: str | Path = DEFAULT_REPORT_DIR,
) -> str:
    """Write a readable timestamped Markdown diagnostic report and return its path."""
    report_dir = ensure_report_dir(output_dir)
    report_path = report_dir / f"diagnostic-network-{filename_timestamp()}.md"

    metadata = report["metadata"]
    system = report["system"]
    network = report["network"]
    resources = report["resources"]
    docker = report["docker"]
    security = report["security"]
    resolv_conf = network["dns"]["resolv_conf"]
    resolver_commands = network["dns"]["resolver_commands"]

    content = f"""# Diagnostic réseau avancé v0.3.0

## Système

- Version du schéma : `{metadata["schema_version"]}`
- Généré en UTC : `{metadata["generated_at_utc"]}`
- Mode : `{metadata["mode"]}`
- Hôte : `{system["hostname"]}`
- Plateforme : `{system["platform"]}`
- Version plateforme : `{system["platform_version"]}`
- Version Python : `{system["python_version"]}`

## Interfaces réseau

{command_block(network["interfaces"])}

## Routes

{command_block(network["routes"])}

## DNS

### /etc/resolv.conf

- Chemin : `{resolv_conf["path"]}`
- Disponible : `{resolv_conf["available"]}`
- Serveurs DNS : `{", ".join(resolv_conf["nameservers"]) or "non détecté"}`
- Domaines de recherche : `{", ".join(resolv_conf["search"]) or "non détecté"}`

```text
{resolv_conf["content"].strip() or "(aucun contenu)"}
```

### Commandes de résolution DNS

{resolver_commands_block(resolver_commands)}

## Ports ouverts

{command_block(network["ports"])}

## Disque

{command_block(resources["disk"])}

## Mémoire

{command_block(resources["memory"])}

## Docker

{command_block(docker)}

## Conclusion

- Diagnostic en lecture seule : `{security["read_only"]}`
- Commandes destructives utilisées : `{security["destructive_commands_used"]}`
- Commandes autorisées : `{len(security["allowed_commands"])}`
- Les données ci-dessus sont destinées au diagnostic local défensif.
- Ne pas exposer `/diag` publiquement sans authentification.
"""
    report_path.write_text(content, encoding="utf-8")
    report_path.chmod(0o600)
    prune_old_reports(report_dir, ".md")
    logger.info("Wrote Markdown diagnostic report: %s", report_path)
    return str(report_path)
