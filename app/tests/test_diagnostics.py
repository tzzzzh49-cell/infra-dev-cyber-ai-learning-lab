import json
import subprocess
import sys

from app import diagnostics


def test_collect_system_info_returns_portable_fields():
    data = diagnostics.collect_system_info()

    assert "hostname" in data
    assert "platform" in data
    assert "platform_version" in data
    assert "python_version" in data


def test_run_read_only_command_simple_python_version():
    data = diagnostics.run_read_only_command([sys.executable, "--version"])

    assert data["command"] == [sys.executable, "--version"]
    assert data["available"] is True
    assert data["returncode"] == 0
    assert "Python" in data["stdout"] or "Python" in data["stderr"]
    assert data["timed_out"] is False


def test_run_read_only_command_handles_missing_command():
    data = diagnostics.run_read_only_command(["command-that-should-not-exist-lab-v030"])

    assert data["available"] is False
    assert data["returncode"] is None
    assert data["timed_out"] is False
    assert data["stderr"]


def test_run_read_only_command_handles_timeout(monkeypatch):
    def fake_run(*_args, **_kwargs):
        raise subprocess.TimeoutExpired(cmd=["slow"], timeout=1)

    monkeypatch.setattr(diagnostics.subprocess, "run", fake_run)

    data = diagnostics.run_read_only_command(["slow"], timeout=1)

    assert data["available"] is True
    assert data["returncode"] is None
    assert data["timed_out"] is True
    assert "timed out" in data["stderr"]


def test_collect_network_diagnostic_sections_exist():
    data = diagnostics.collect_network_diagnostic()

    assert data["metadata"]["schema_version"] == "0.3.0"
    assert data["metadata"]["mode"] == "read-only"
    assert "system" in data
    assert "network" in data
    assert "interfaces" in data["network"]
    assert "routes" in data["network"]
    assert "dns" in data["network"]
    assert "ports" in data["network"]
    assert "resources" in data
    assert "disk" in data["resources"]
    assert "memory" in data["resources"]
    assert "docker" in data
    assert data["security"]["read_only"] is True
    assert data["security"]["destructive_commands_used"] is False


def test_write_json_report_uses_requested_directory(tmp_path):
    report = diagnostics.collect_network_diagnostic()

    path = diagnostics.write_json_report(report, output_dir=str(tmp_path))

    assert path.startswith(str(tmp_path))
    assert path.endswith(".json")
    saved = json.loads((tmp_path / path.split("/")[-1]).read_text(encoding="utf-8"))
    assert saved["metadata"]["schema_version"] == "0.3.0"


def test_write_markdown_report_uses_requested_directory(tmp_path):
    report = diagnostics.collect_network_diagnostic()

    path = diagnostics.write_markdown_report(report, output_dir=str(tmp_path))

    assert path.startswith(str(tmp_path))
    assert path.endswith(".md")
    content = (tmp_path / path.split("/")[-1]).read_text(encoding="utf-8")
    assert "# Diagnostic réseau avancé v0.3.0" in content
    assert "## Interfaces réseau" in content
    assert "## Conclusion" in content


def test_parse_json_output_returns_dict():
    data = diagnostics.parse_json_output({"stdout": '{"status": "ok"}'})

    assert data == {"status": "ok"}


def test_parse_json_output_returns_none_for_invalid_json():
    data = diagnostics.parse_json_output({"stdout": "not-json"})

    assert data is None


def test_parse_json_lines_preserves_invalid_lines():
    data = diagnostics.parse_json_lines(
        {"stdout": '{"name": "api"}\nnot-json\n{"name": "worker"}\n'}
    )

    assert data == [
        {"name": "api"},
        {"raw": "not-json"},
        {"name": "worker"},
    ]


def test_read_resolv_conf_uses_requested_file(tmp_path):
    resolv_conf = tmp_path / "resolv.conf"
    resolv_conf.write_text(
        "# test\nnameserver 1.1.1.1\nsearch lab.local example.test\noptions edns0\n",
        encoding="utf-8",
    )

    data = diagnostics.read_resolv_conf(str(resolv_conf))

    assert data["path"] == str(resolv_conf)
    assert data["available"] is True
    assert data["nameservers"] == ["1.1.1.1"]
    assert data["search"] == ["lab.local", "example.test"]
    assert data["options"] == ["edns0"]
