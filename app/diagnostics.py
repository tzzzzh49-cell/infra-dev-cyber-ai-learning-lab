"""Read-only diagnostic helpers for the local learning lab.

The module intentionally uses only Python's standard library and only runs
non-destructive commands without ``shell=True``.
"""

from __future__ import annotations

import json
import platform
import socket
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "0.3.0"
DEFAULT_REPORT_DIR = "outputs/reports"


def utc_now_iso() -> str:
    """Return the current UTC time as an ISO-8601 string."""
    return datetime.now(UTC).isoformat()


def safe_timestamp() -> str:
    """Return a filesystem-friendly UTC timestamp."""
    return datetime.now(UTC).strftime("%Y-%m-%d-%H%M%S")


def run_read_only_command(command: list[str], timeout: int = 3) -> dict[str, Any]:
    """Run a read-only command and return a stable execution dictionary.

    The command is executed without a shell, with captured output and a short
    timeout. Missing commands and timeouts are represented in the returned
    dictionary instead of being raised to callers.
    """
    result: dict[str, Any] = {
        "command": command,
        "available": False,
        "returncode": None,
        "stdout": "",
        "stderr": "",
        "timed_out": False,
    }

    if not command:
        result["stderr"] = "empty command"
        return result

    try:
        completed = subprocess.run(  # noqa: S603 - command lists are fixed by callers, no shell.
            command,
            capture_output=True,
            text=True,
            check=False,
            timeout=timeout,
        )
    except FileNotFoundError as exc:
        result["stderr"] = str(exc)
        return result
    except subprocess.TimeoutExpired as exc:
        result["available"] = True
        result["timed_out"] = True
        result["stdout"] = _coerce_output(exc.stdout)
        result["stderr"] = _coerce_output(exc.stderr) or f"Timeout after {timeout}s"
        return result

    result["available"] = True
    result["returncode"] = completed.returncode
    result["stdout"] = completed.stdout
    result["stderr"] = completed.stderr
    return result


def _coerce_output(value: str | bytes | None) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode(errors="replace")
    return value


def parse_json_output(command_result: dict[str, Any]) -> Any:
    """Parse JSON stdout from a command result, returning None on failure."""
    if not command_result.get("stdout"):
        return None
    try:
        return json.loads(command_result["stdout"])
    except json.JSONDecodeError:
        return None


def parse_json_lines_output(command_result: dict[str, Any]) -> list[Any]:
    """Parse newline-delimited JSON stdout from a command result."""
    parsed: list[Any] = []
    for line in command_result.get("stdout", "").splitlines():
        if not line.strip():
            continue
        try:
            parsed.append(json.loads(line))
        except json.JSONDecodeError:
            parsed.append({"raw": line})
    return parsed


def collect_system_info() -> dict[str, str]:
    """Collect basic system information using the standard library."""
    return {
        "hostname": socket.gethostname(),
        "platform": platform.system(),
        "platform_version": platform.version(),
        "python_version": platform.python_version(),
    }


def read_resolv_conf(path: str = "/etc/resolv.conf") -> dict[str, Any]:
    """Read /etc/resolv.conf in a tolerant, read-only way."""
    resolv_path = Path(path)
    try:
        content = resolv_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return {
            "path": path,
            "available": False,
            "content": "",
            "error": "file not found",
        }
    except OSError as exc:
        return {"path": path, "available": False, "content": "", "error": str(exc)}

    nameservers = []
    search = []
    for line in content.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        parts = stripped.split()
        if parts[0] == "nameserver" and len(parts) > 1:
            nameservers.append(parts[1])
        elif parts[0] == "search" and len(parts) > 1:
            search.extend(parts[1:])

    return {
        "path": path,
        "available": True,
        "content": content,
        "nameservers": nameservers,
        "search": search,
    }


def collect_dns_info() -> dict[str, Any]:
    """Collect DNS information from resolv.conf and resolvectl if available."""
    resolvectl_dns = run_read_only_command(["resolvectl", "dns"])
    if not resolvectl_dns["available"]:
        resolvectl = run_read_only_command(["resolvectl", "status"])
    else:
        resolvectl = resolvectl_dns

    return {
        "resolv_conf": read_resolv_conf(),
        "resolvectl": resolvectl,
    }


def collect_network_diagnostic() -> dict[str, Any]:
    """Collect a structured, read-only system and network diagnostic report."""
    interfaces = run_read_only_command(["ip", "-j", "addr"])
    routes = run_read_only_command(["ip", "-j", "route"])
    ports = run_read_only_command(["ss", "-tulpn"])
    disk = run_read_only_command(["df", "-h"])
    memory = run_read_only_command(["free", "-h"])
    docker = run_read_only_command(["docker", "ps", "--format", "{{json .}}"])

    interfaces["parsed"] = parse_json_output(interfaces)
    routes["parsed"] = parse_json_output(routes)
    docker["parsed"] = parse_json_lines_output(docker)

    return {
        "metadata": {
            "schema_version": SCHEMA_VERSION,
            "generated_at_utc": utc_now_iso(),
            "mode": "read-only",
        },
        "system": collect_system_info(),
        "network": {
            "interfaces": interfaces,
            "routes": routes,
            "dns": collect_dns_info(),
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
        },
    }


def write_json_report(
    report: dict[str, Any],
    output_dir: str = DEFAULT_REPORT_DIR,
) -> str:
    """Write a timestamped JSON report and return its path."""
    report_dir = Path(output_dir)
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / f"diagnostic-network-{safe_timestamp()}.json"
    report_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return str(report_path)


def write_markdown_report(
    report: dict[str, Any],
    output_dir: str = DEFAULT_REPORT_DIR,
) -> str:
    """Write a timestamped Markdown report and return its path."""
    report_dir = Path(output_dir)
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / f"diagnostic-network-{safe_timestamp()}.md"
    report_path.write_text(render_markdown_report(report), encoding="utf-8")
    return str(report_path)


def render_markdown_report(report: dict[str, Any]) -> str:
    """Render a structured diagnostic report as readable Markdown."""
    metadata = report.get("metadata", {})
    system = report.get("system", {})
    network = report.get("network", {})
    resources = report.get("resources", {})

    lines = [
        "# Diagnostic réseau avancé v0.3.0",
        "",
        f"- Généré UTC : {metadata.get('generated_at_utc', 'inconnu')}",
        f"- Mode : {metadata.get('mode', 'read-only')}",
        f"- Schéma : {metadata.get('schema_version', SCHEMA_VERSION)}",
        "",
        "## Système",
        "",
        f"- Hostname : {system.get('hostname', 'inconnu')}",
        f"- Plateforme : {system.get('platform', 'inconnu')}",
        f"- Version plateforme : {system.get('platform_version', 'inconnu')}",
        f"- Version Python : {system.get('python_version', 'inconnu')}",
        "",
    ]

    _append_command_section(
        lines, "Interfaces", network.get("interfaces", {}), prefer_parsed=True
    )
    _append_command_section(
        lines, "Routes", network.get("routes", {}), prefer_parsed=True
    )
    _append_dns_section(lines, network.get("dns", {}))
    _append_command_section(lines, "Ports", network.get("ports", {}))
    _append_command_section(lines, "Disque", resources.get("disk", {}))
    _append_command_section(lines, "Mémoire", resources.get("memory", {}))
    _append_command_section(
        lines, "Docker", report.get("docker", {}), prefer_parsed=True
    )

    lines.extend([
        "## Conclusion",
        "",
        "Diagnostic généré en mode lecture seule. Les commandes absentes ou "
        "indisponibles sont signalées dans chaque section sans arrêter la collecte.",
        "",
    ])
    return "\n".join(lines)


def _append_dns_section(lines: list[str], dns: dict[str, Any]) -> None:
    lines.extend(["## DNS", ""])
    resolv_conf = dns.get("resolv_conf", {})
    lines.extend([
        f"- Fichier : {resolv_conf.get('path', '/etc/resolv.conf')}",
        f"- Disponible : {resolv_conf.get('available', False)}",
        "- Nameservers : "
        f"{', '.join(resolv_conf.get('nameservers', [])) or 'non détecté'}",
        "",
        "### /etc/resolv.conf",
        "",
        "```",
        resolv_conf.get("content", ""),
        "```",
        "",
    ])
    _append_command_section(
        lines, "resolvectl", dns.get("resolvectl", {}), heading_level="###"
    )


def _append_command_section(
    lines: list[str],
    title: str,
    command_result: dict[str, Any],
    *,
    prefer_parsed: bool = False,
    heading_level: str = "##",
) -> None:
    lines.extend([f"{heading_level} {title}", ""])
    command = command_result.get("command", [])
    lines.extend([
        f"- Commande : `{' '.join(command) if command else 'n/a'}`",
        f"- Disponible : {command_result.get('available', False)}",
        f"- Code retour : {command_result.get('returncode')}",
        f"- Timeout : {command_result.get('timed_out', False)}",
        "",
    ])

    if prefer_parsed and command_result.get("parsed") is not None:
        lines.extend([
            "```json",
            json.dumps(command_result["parsed"], ensure_ascii=False, indent=2),
            "```",
            "",
        ])
        return

    stdout = command_result.get("stdout") or ""
    stderr = command_result.get("stderr") or ""
    lines.extend(["```", stdout or stderr or "Aucune sortie.", "```", ""])
