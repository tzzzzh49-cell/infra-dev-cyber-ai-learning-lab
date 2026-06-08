import json
import sys

from app.diagnostics import (
    collect_network_diagnostic,
    collect_system_info,
    run_read_only_command,
    write_json_report,
    write_markdown_report,
)


def test_collect_system_info_returns_basic_keys():
    data = collect_system_info()

    assert "hostname" in data
    assert "platform" in data
    assert "platform_version" in data
    assert "python_version" in data


def test_collect_network_diagnostic_returns_main_sections():
    data = collect_network_diagnostic()

    assert "metadata" in data
    assert "system" in data
    assert "network" in data
    assert "resources" in data
    assert "docker" in data
    assert "security" in data
    assert "interfaces" in data["network"]
    assert "routes" in data["network"]
    assert "dns" in data["network"]
    assert "ports" in data["network"]
    assert "disk" in data["resources"]
    assert "memory" in data["resources"]


def test_run_read_only_command_simple_command():
    data = run_read_only_command([sys.executable, "--version"])

    assert data["command"] == [sys.executable, "--version"]
    assert data["available"] is True
    assert data["returncode"] == 0
    assert "Python" in data["stdout"] or "Python" in data["stderr"]
    assert data["timed_out"] is False


def test_run_read_only_command_missing_command():
    data = run_read_only_command(["definitely-missing-command-v030"])

    assert data["available"] is False
    assert data["returncode"] is None
    assert data["timed_out"] is False
    assert data["stderr"]


def test_write_json_report_writes_file(tmp_path):
    report = collect_network_diagnostic()
    path = write_json_report(report, output_dir=str(tmp_path))

    saved = tmp_path / path.split("/")[-1]
    assert saved.exists()
    saved_report = json.loads(saved.read_text(encoding="utf-8"))
    assert saved_report["metadata"]["schema_version"] == "0.3.0"


def test_write_markdown_report_writes_file(tmp_path):
    report = collect_network_diagnostic()
    path = write_markdown_report(report, output_dir=str(tmp_path))

    saved = tmp_path / path.split("/")[-1]
    assert saved.exists()
    content = saved.read_text(encoding="utf-8")
    assert "# Diagnostic réseau avancé v0.3.0" in content
    assert "## Système" in content
    assert "## Interfaces" in content
    assert "## Conclusion" in content
