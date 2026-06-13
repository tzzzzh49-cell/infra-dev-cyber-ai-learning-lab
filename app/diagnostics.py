"""Read-only diagnostic helpers for the local learning lab."""

import json
import platform
import socket
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "0.3.0"
DEFAULT_REPORT_DIR = "outputs/reports"


def utc_timestamp() -> str:
    """Return an ISO-8601 UTC timestamp."""
    return datetime.now(UTC).isoformat()


def filename_timestamp() -> str:
    """Return a filesystem-friendly UTC timestamp."""
    return datetime.now(UTC).strftime("%Y-%m-%d-%H%M%S-%f")


def run_read_only_command(command: list[str], timeout: int = 3) -> dict[str, Any]:
    """Run a short read-only command without a shell and return a stable result."""
    result: dict[str, Any] = {
        "command": command,
        "available": False,
        "returncode": None,
        "stdout": "",
        "stderr": "",
        "timed_out": False,
    }

    try:
        completed = subprocess.run(
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
        result["stdout"] = exc.stdout or ""
        result["stderr"] = exc.stderr or f"Command timed out after {timeout}s"
        return result

    result["available"] = True
    result["returncode"] = completed.returncode
    result["stdout"] = completed.stdout
    result["stderr"] = completed.stderr
    return result


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


def collect_resolvectl() -> dict[str, Any]:
    """Collect DNS information from resolvectl when available."""
    dns_result = run_read_only_command(["resolvectl", "dns"])
    if dns_result["available"] and dns_result["returncode"] == 0:
        return dns_result

    status_result = run_read_only_command(["resolvectl", "status"])
    status_result["fallback_from"] = dns_result
    return status_result


def command_with_parsed_json(command: list[str]) -> dict[str, Any]:
    """Run a command and attach parsed JSON output when valid."""
    result = run_read_only_command(command)
    result["parsed"] = parse_json_output(result)
    return result


def collect_network_diagnostic() -> dict[str, Any]:
    """Collect an advanced read-only system and network diagnostic."""
    interfaces = command_with_parsed_json(["ip", "-j", "addr"])
    routes = command_with_parsed_json(["ip", "-j", "route"])
    ports = run_read_only_command(["ss", "-tulpn"])
    disk = run_read_only_command(["df", "-h"])
    memory = run_read_only_command(["free", "-h"])
    docker = run_read_only_command(["docker", "ps", "--format", "{{json .}}"])
    docker["parsed"] = parse_json_lines(docker)

    return {
        "metadata": {
            "schema_version": SCHEMA_VERSION,
            "generated_at_utc": utc_timestamp(),
            "mode": "read-only",
        },
        "system": collect_system_info(),
        "network": {
            "interfaces": interfaces,
            "routes": routes,
            "dns": {
                "resolv_conf": read_resolv_conf(),
                "resolvectl": collect_resolvectl(),
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


def ensure_report_dir(output_dir: str) -> Path:
    """Create and return the report directory path."""
    report_dir = Path(output_dir)
    report_dir.mkdir(parents=True, exist_ok=True)
    return report_dir


def write_json_report(
    report: dict[str, Any],
    output_dir: str = DEFAULT_REPORT_DIR,
) -> str:
    """Write a timestamped JSON diagnostic report and return its path."""
    report_dir = ensure_report_dir(output_dir)
    report_path = report_dir / f"diagnostic-network-{filename_timestamp()}.json"
    report_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
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


def write_markdown_report(
    report: dict[str, Any],
    output_dir: str = DEFAULT_REPORT_DIR,
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

### resolvectl

{command_block(network["dns"]["resolvectl"])}

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
- Les données ci-dessus sont destinées au diagnostic local défensif.
- Ne pas exposer `/diag` publiquement sans authentification.
"""
    report_path.write_text(content, encoding="utf-8")
    return str(report_path)
