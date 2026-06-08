"""Read-only system and network diagnostics for the local lab."""

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


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _timestamp_for_filename() -> str:
    return _utc_now().strftime("%Y-%m-%d-%H%M%S")


def run_read_only_command(command: list[str], timeout: int = 3) -> dict[str, Any]:
    """Run a short read-only command without invoking a shell."""
    result: dict[str, Any] = {
        "command": command,
        "available": True,
        "returncode": None,
        "stdout": "",
        "stderr": "",
        "timed_out": False,
    }

    try:
        completed = subprocess.run(  # noqa: S603 - commands are fixed read-only probes.
            command,
            capture_output=True,
            text=True,
            check=False,
            timeout=timeout,
        )
    except FileNotFoundError as exc:
        result.update(
            {
                "available": False,
                "stderr": str(exc),
            }
        )
    except subprocess.TimeoutExpired as exc:
        result.update(
            {
                "returncode": None,
                "stdout": exc.stdout or "",
                "stderr": exc.stderr or "",
                "timed_out": True,
            }
        )
    else:
        result.update(
            {
                "returncode": completed.returncode,
                "stdout": completed.stdout,
                "stderr": completed.stderr,
            }
        )

    return result


def collect_system_info() -> dict[str, str]:
    """Collect stable system metadata using only the Python standard library."""
    return {
        "hostname": socket.gethostname(),
        "platform": platform.system(),
        "platform_version": platform.version(),
        "python_version": platform.python_version(),
    }


def _parse_json_command(command_result: dict[str, Any]) -> dict[str, Any]:
    parsed_result = dict(command_result)
    parsed_result["parsed"] = []

    if not command_result["available"] or command_result["timed_out"]:
        return parsed_result

    stdout = command_result.get("stdout", "").strip()
    if not stdout:
        return parsed_result

    try:
        parsed_result["parsed"] = json.loads(stdout)
    except json.JSONDecodeError as exc:
        parsed_result["parse_error"] = str(exc)

    return parsed_result


def _parse_json_lines_command(command_result: dict[str, Any]) -> dict[str, Any]:
    parsed_result = dict(command_result)
    parsed_result["parsed"] = []

    if not command_result["available"] or command_result["timed_out"]:
        return parsed_result

    parse_errors = []
    for line_number, line in enumerate(
        command_result.get("stdout", "").splitlines(), start=1
    ):
        stripped_line = line.strip()
        if not stripped_line:
            continue
        try:
            parsed_result["parsed"].append(json.loads(stripped_line))
        except json.JSONDecodeError as exc:
            parse_errors.append({"line": line_number, "error": str(exc)})

    if parse_errors:
        parsed_result["parse_errors"] = parse_errors

    return parsed_result


def _read_resolv_conf(path: str = "/etc/resolv.conf") -> dict[str, Any]:
    resolv_path = Path(path)
    result: dict[str, Any] = {
        "path": path,
        "available": False,
        "content": "",
        "nameservers": [],
        "search": [],
        "options": [],
    }

    try:
        content = resolv_path.read_text(encoding="utf-8", errors="replace")
    except FileNotFoundError:
        result["error"] = "file not found"
        return result

    result["available"] = True
    result["content"] = content

    for line in content.splitlines():
        stripped_line = line.strip()
        if not stripped_line or stripped_line.startswith("#"):
            continue
        key, _, value = stripped_line.partition(" ")
        values = value.split()
        if key == "nameserver" and value:
            result["nameservers"].append(value.strip())
        elif key == "search":
            result["search"].extend(values)
        elif key == "options":
            result["options"].extend(values)

    return result


def _collect_resolvectl() -> dict[str, Any]:
    dns_result = run_read_only_command(["resolvectl", "dns"])
    if dns_result["available"] and not dns_result["timed_out"]:
        return dns_result
    status_result = run_read_only_command(["resolvectl", "status"])
    status_result["fallback_reason"] = {
        "dns_available": dns_result["available"],
        "dns_timed_out": dns_result["timed_out"],
        "dns_returncode": dns_result["returncode"],
    }
    return status_result


def collect_network_diagnostic() -> dict[str, Any]:
    """Collect a read-only system and network diagnostic report."""
    interfaces = _parse_json_command(run_read_only_command(["ip", "-j", "addr"]))
    routes = _parse_json_command(run_read_only_command(["ip", "-j", "route"]))
    ports = run_read_only_command(["ss", "-tulpn"])
    disk = run_read_only_command(["df", "-h"])
    memory = run_read_only_command(["free", "-h"])
    docker = _parse_json_lines_command(
        run_read_only_command(["docker", "ps", "--format", "{{json .}}"], timeout=5)
    )

    return {
        "metadata": {
            "schema_version": SCHEMA_VERSION,
            "generated_at_utc": _utc_now().isoformat(),
            "mode": "read-only",
        },
        "system": collect_system_info(),
        "network": {
            "interfaces": interfaces,
            "routes": routes,
            "dns": {
                "resolv_conf": _read_resolv_conf(),
                "resolvectl": _collect_resolvectl(),
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
        },
    }


def _prepare_output_dir(output_dir: str) -> Path:
    report_dir = Path(output_dir)
    report_dir.mkdir(parents=True, exist_ok=True)
    return report_dir


def write_json_report(
    report: dict[str, Any], output_dir: str = DEFAULT_REPORT_DIR
) -> str:
    """Write a timestamped JSON report and return its path."""
    report_dir = _prepare_output_dir(output_dir)
    report_path = report_dir / f"network-diagnostic-{_timestamp_for_filename()}.json"
    report_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return str(report_path)


def _command_block(section: dict[str, Any]) -> str:
    command = " ".join(section.get("command", []))
    stdout = section.get("stdout") or ""
    stderr = section.get("stderr") or ""
    details = [f"Commande : `{command}`" if command else "Commande : non applicable"]
    details.append(f"Disponible : `{section.get('available')}`")
    details.append(f"Code retour : `{section.get('returncode')}`")
    details.append(f"Timeout : `{section.get('timed_out')}`")
    if stdout:
        details.extend(["", "```text", stdout.rstrip(), "```"])
    if stderr:
        details.extend(["", "Erreur standard :", "```text", stderr.rstrip(), "```"])
    return "\n".join(details)


def write_markdown_report(
    report: dict[str, Any], output_dir: str = DEFAULT_REPORT_DIR
) -> str:
    """Write a timestamped Markdown report and return its path."""
    report_dir = _prepare_output_dir(output_dir)
    report_path = report_dir / f"network-diagnostic-{_timestamp_for_filename()}.md"

    system = report.get("system", {})
    network = report.get("network", {})
    resources = report.get("resources", {})
    dns = network.get("dns", {})
    resolv_conf = dns.get("resolv_conf", {})

    lines = [
        "# Diagnostic réseau avancé v0.3.0",
        "",
        "## Métadonnées",
        "",
        f"- Schéma : `{report.get('metadata', {}).get('schema_version')}`",
        f"- Généré UTC : `{report.get('metadata', {}).get('generated_at_utc')}`",
        f"- Mode : `{report.get('metadata', {}).get('mode')}`",
        "",
        "## Système",
        "",
        f"- Hôte : `{system.get('hostname')}`",
        f"- Plateforme : `{system.get('platform')}`",
        f"- Version plateforme : `{system.get('platform_version')}`",
        f"- Version Python : `{system.get('python_version')}`",
        "",
        "## Interfaces réseau",
        "",
        _command_block(network.get("interfaces", {})),
        "",
        "## Routes",
        "",
        _command_block(network.get("routes", {})),
        "",
        "## DNS",
        "",
        f"Fichier : `{resolv_conf.get('path')}`",
        f"Disponible : `{resolv_conf.get('available')}`",
        f"Nameservers : `{', '.join(resolv_conf.get('nameservers', []))}`",
        "",
        "### resolvectl",
        "",
        _command_block(dns.get("resolvectl", {})),
        "",
        "## Ports ouverts",
        "",
        _command_block(network.get("ports", {})),
        "",
        "## Disque",
        "",
        _command_block(resources.get("disk", {})),
        "",
        "## Mémoire",
        "",
        _command_block(resources.get("memory", {})),
        "",
        "## Docker",
        "",
        _command_block(report.get("docker", {})),
        "",
        "## Conclusion",
        "",
        (
            "Diagnostic généré en mode lecture seule. "
            "Aucune commande destructive n'a été utilisée."
        ),
        "",
    ]

    report_path.write_text("\n".join(lines), encoding="utf-8")
    return str(report_path)
