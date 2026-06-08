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
    return datetime.now(UTC).isoformat()


def run_read_only_command(command: list[str], timeout: int = 3) -> dict[str, Any]:
    """Run a read-only command without shell expansion and return a stable result."""
    result: dict[str, Any] = {
        "command": command,
        "available": True,
        "returncode": None,
        "stdout": "",
        "stderr": "",
        "timeout": False,
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
        result.update(
            {
                "available": False,
                "stderr": str(exc),
                "returncode": None,
            }
        )
        return result
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout if isinstance(exc.stdout, str) else ""
        stderr = exc.stderr if isinstance(exc.stderr, str) else ""
        result.update(
            {
                "available": True,
                "stdout": stdout,
                "stderr": stderr or f"Command timed out after {timeout} seconds.",
                "timeout": True,
            }
        )
        return result

    result.update(
        {
            "returncode": completed.returncode,
            "stdout": completed.stdout,
            "stderr": completed.stderr,
        }
    )
    return result


def collect_system_info() -> dict[str, str]:
    return {
        "hostname": socket.gethostname(),
        "platform": platform.system(),
        "platform_version": platform.version(),
        "python_version": platform.python_version(),
    }


def parse_json_command(command_result: dict[str, Any]) -> dict[str, Any]:
    parsed_result = dict(command_result)
    if not command_result.get("available") or command_result.get("returncode") != 0:
        parsed_result["parsed"] = []
        return parsed_result

    try:
        parsed_result["parsed"] = json.loads(command_result.get("stdout", "") or "[]")
    except json.JSONDecodeError as exc:
        parsed_result["parsed"] = []
        parsed_result["parse_error"] = str(exc)
    return parsed_result


def parse_json_lines_command(command_result: dict[str, Any]) -> dict[str, Any]:
    parsed_result = dict(command_result)
    parsed: list[Any] = []
    errors: list[str] = []

    if command_result.get("available") and command_result.get("returncode") == 0:
        for line in command_result.get("stdout", "").splitlines():
            if not line.strip():
                continue
            try:
                parsed.append(json.loads(line))
            except json.JSONDecodeError as exc:
                errors.append(str(exc))

    parsed_result["parsed"] = parsed
    if errors:
        parsed_result["parse_errors"] = errors
    return parsed_result


def read_resolv_conf(path: str = "/etc/resolv.conf") -> dict[str, Any]:
    try:
        content = Path(path).read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        return {"path": path, "available": False, "content": "", "error": str(exc)}
    except OSError as exc:
        return {"path": path, "available": False, "content": "", "error": str(exc)}
    return {"path": path, "available": True, "content": content}


def collect_dns_info() -> dict[str, Any]:
    resolvectl_dns = run_read_only_command(["resolvectl", "dns"])
    if not resolvectl_dns["available"] or resolvectl_dns["returncode"] != 0:
        resolvectl = run_read_only_command(["resolvectl", "status"])
    else:
        resolvectl = resolvectl_dns

    return {
        "resolv_conf": read_resolv_conf(),
        "resolvectl": resolvectl,
    }


def collect_network_diagnostic() -> dict[str, Any]:
    interfaces = parse_json_command(run_read_only_command(["ip", "-j", "addr"]))
    routes = parse_json_command(run_read_only_command(["ip", "-j", "route"]))
    ports = run_read_only_command(["ss", "-tulpn"])
    disk = run_read_only_command(["df", "-h"])
    memory = run_read_only_command(["free", "-h"])
    docker = parse_json_lines_command(
        run_read_only_command(["docker", "ps", "--format", "{{json .}}"])
    )

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


def ensure_report_dir(output_dir: str) -> Path:
    report_dir = Path(output_dir)
    report_dir.mkdir(parents=True, exist_ok=True)
    return report_dir


def report_timestamp() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%d-%H%M%S")


def write_json_report(
    report: dict[str, Any],
    output_dir: str = DEFAULT_REPORT_DIR,
) -> str:
    report_dir = ensure_report_dir(output_dir)
    report_path = report_dir / f"diagnostic-network-{report_timestamp()}.json"
    report_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return str(report_path)


def command_summary(section: dict[str, Any]) -> str:
    if not section.get("available"):
        return "Commande indisponible."
    if section.get("timeout"):
        return "Commande interrompue par timeout."
    return f"Code retour : {section.get('returncode')}"


def code_block(content: str) -> str:
    clean_content = content.rstrip() if content else "Aucune sortie."
    return f"```\n{clean_content}\n```"


def markdown_command_section(title: str, section: dict[str, Any]) -> list[str]:
    command = " ".join(section.get("command", []))
    lines = [
        f"## {title}",
        "",
        f"Commande : `{command}`",
        "",
        command_summary(section),
        "",
    ]
    if "parsed" in section:
        parsed_json = json.dumps(section["parsed"], ensure_ascii=False, indent=2)
        lines.extend(["Données parsées :", "", code_block(parsed_json), ""])
    lines.extend(["Sortie brute :", "", code_block(section.get("stdout", "")), ""])
    if section.get("stderr"):
        lines.extend(["Erreur standard :", "", code_block(section["stderr"]), ""])
    return lines


def write_markdown_report(
    report: dict[str, Any],
    output_dir: str = DEFAULT_REPORT_DIR,
) -> str:
    report_dir = ensure_report_dir(output_dir)
    report_path = report_dir / f"diagnostic-network-{report_timestamp()}.md"

    dns = report["network"]["dns"]
    resolv_conf = dns["resolv_conf"]
    lines = [
        "# Rapport de diagnostic réseau avancé",
        "",
        f"Date UTC : {report['metadata']['generated_at_utc']}",
        f"Version de schéma : {report['metadata']['schema_version']}",
        f"Mode : {report['metadata']['mode']}",
        "",
        "## Système",
        "",
        f"- Hostname : `{report['system']['hostname']}`",
        f"- Plateforme : `{report['system']['platform']}`",
        f"- Version plateforme : `{report['system']['platform_version']}`",
        f"- Version Python : `{report['system']['python_version']}`",
        "",
    ]

    lines.extend(
        markdown_command_section("Interfaces réseau", report["network"]["interfaces"])
    )
    lines.extend(markdown_command_section("Routes", report["network"]["routes"]))
    lines.extend(
        [
            "## DNS",
            "",
            f"Fichier resolv.conf : `{resolv_conf['path']}`",
            f"Disponible : `{resolv_conf['available']}`",
            "",
            code_block(resolv_conf.get("content", "")),
            "",
        ]
    )
    lines.extend(markdown_command_section("DNS resolvectl", dns["resolvectl"]))
    lines.extend(markdown_command_section("Ports ouverts", report["network"]["ports"]))
    lines.extend(markdown_command_section("Disque", report["resources"]["disk"]))
    lines.extend(markdown_command_section("Mémoire", report["resources"]["memory"]))
    lines.extend(markdown_command_section("Docker", report["docker"]))
    lines.extend(
        [
            "## Conclusion",
            "",
            "Diagnostic généré en mode lecture seule. Aucune commande destructive, "
            "sudo, modification réseau ou action Docker destructive n'a été exécutée.",
            "",
            f"- Lecture seule : `{report['security']['read_only']}`",
            "- Commandes destructives utilisées : "
            f"`{report['security']['destructive_commands_used']}`",
            "",
        ]
    )

    report_path.write_text("\n".join(lines), encoding="utf-8")
    return str(report_path)
