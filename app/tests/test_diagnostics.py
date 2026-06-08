import json
import sys
from pathlib import Path

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


def test_run_read_only_command_with_python_version():
    result = run_read_only_command([sys.executable, "--version"])

    assert result["command"] == [sys.executable, "--version"]
    assert result["available"] is True
    assert result["returncode"] == 0
    assert "Python" in result["stdout"] or "Python" in result["stderr"]
    assert result["timeout"] is False


def test_run_read_only_command_when_command_is_missing():
    result = run_read_only_command(["command-that-should-not-exist-v030"])

    assert result["available"] is False
    assert result["returncode"] is None
    assert result["stderr"]


def test_write_json_report_in_temporary_directory(tmp_path: Path):
    report = collect_network_diagnostic()
    path = write_json_report(report, output_dir=str(tmp_path))

    report_path = Path(path)
    assert report_path.exists()
    assert report_path.parent == tmp_path
    assert report_path.suffix == ".json"
    data = json.loads(report_path.read_text(encoding="utf-8"))
    assert data["metadata"]["schema_version"] == "0.3.0"


def test_write_markdown_report_in_temporary_directory(tmp_path: Path):
    report = collect_network_diagnostic()
    path = write_markdown_report(report, output_dir=str(tmp_path))

    report_path = Path(path)
    assert report_path.exists()
    assert report_path.parent == tmp_path
    assert report_path.suffix == ".md"
    content = report_path.read_text(encoding="utf-8")
    assert "# Rapport de diagnostic réseau avancé" in content
    assert "## Interfaces réseau" in content
    assert "## Conclusion" in content
