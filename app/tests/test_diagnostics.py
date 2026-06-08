import json
import subprocess
import sys

from app import diagnostics
from app.diagnostics import (
    collect_network_diagnostic,
    collect_system_info,
    run_read_only_command,
    write_json_report,
    write_markdown_report,
)


def test_collect_system_info_returns_expected_keys():
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
    assert data["security"]["destructive_commands_used"] is False


def test_run_read_only_command_with_python_version():
    result = run_read_only_command([sys.executable, "--version"])

    assert result["command"] == [sys.executable, "--version"]
    assert result["available"] is True
    assert result["timed_out"] is False
    assert result["returncode"] == 0
    assert "Python" in result["stdout"] or "Python" in result["stderr"]


def test_run_read_only_command_handles_missing_command():
    result = run_read_only_command(["definitely-missing-command-for-lab-tests"])

    assert result["available"] is False
    assert result["returncode"] is None
    assert result["timed_out"] is False
    assert result["stderr"]


def test_run_read_only_command_handles_timeout(monkeypatch):
    def fake_run(*args, **kwargs):
        raise subprocess.TimeoutExpired(cmd=kwargs.get("args", ["slow"]), timeout=1)

    monkeypatch.setattr(diagnostics.subprocess, "run", fake_run)

    result = run_read_only_command(["slow"], timeout=1)

    assert result["available"] is True
    assert result["timed_out"] is True
    assert result["returncode"] is None


def test_write_json_report_creates_timestamped_file(tmp_path):
    report = collect_network_diagnostic()

    path = write_json_report(report, output_dir=str(tmp_path))

    assert path.endswith(".json")
    saved_report = json.loads(tmp_path.joinpath(path.split("/")[-1]).read_text())
    assert saved_report["metadata"]["schema_version"] == "0.3.0"
    assert saved_report["security"]["read_only"] is True


def test_write_markdown_report_creates_readable_file(tmp_path):
    report = collect_network_diagnostic()

    path = write_markdown_report(report, output_dir=str(tmp_path))

    assert path.endswith(".md")
    content = tmp_path.joinpath(path.split("/")[-1]).read_text()
    assert "# Diagnostic réseau avancé v0.3.0" in content
    assert "## Système" in content
    assert "## Interfaces réseau" in content
    assert "## Conclusion" in content
