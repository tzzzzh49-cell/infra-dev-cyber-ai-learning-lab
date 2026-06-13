from app.main import (
    APP_VERSION,
    app,
    diag,
    export_diag_json,
    export_diag_markdown,
    health,
    root,
    version,
)


def route_methods(path):
    for route in app.routes:
        if route.path == path:
            return route.methods or set()
    return set()


def test_app_registers_expected_routes():
    expected_routes = {
        "/": "GET",
        "/health": "GET",
        "/version": "GET",
        "/diag": "GET",
        "/diag/export/json": "POST",
        "/diag/export/markdown": "POST",
    }

    for path, method in expected_routes.items():
        assert method in route_methods(path)


def test_get_root_returns_available_endpoints():
    data = root()

    assert data["message"] == "Mini API locale active"
    assert "/health" in data["endpoints"]
    assert "/version" in data["endpoints"]
    assert "/diag" in data["endpoints"]
    assert "/diag/export/json" in data["endpoints"]
    assert "/diag/export/markdown" in data["endpoints"]


def test_get_health_returns_ok_status():
    assert health() == {"status": "ok", "service": "lab-api"}


def test_get_version_returns_app_version():
    assert version() == {
        "app": "infra-dev-cyber-ai-learning-lab-api",
        "version": APP_VERSION,
    }


def test_get_diag_returns_structured_diagnostic(monkeypatch):
    monkeypatch.setattr(
        "app.main.collect_network_diagnostic",
        lambda: {
            "metadata": {"schema_version": APP_VERSION},
            "system": {},
            "network": {},
            "resources": {},
            "docker": {},
            "security": {},
        },
    )

    data = diag()

    assert "metadata" in data
    assert "system" in data
    assert "network" in data
    assert "resources" in data
    assert "docker" in data
    assert "security" in data


def test_post_diag_export_json_uses_isolated_output(tmp_path, monkeypatch):
    report = {
        "metadata": {"schema_version": APP_VERSION},
        "system": {},
        "network": {},
        "resources": {},
        "docker": {},
        "security": {},
    }
    monkeypatch.setattr("app.main.collect_network_diagnostic", lambda: report)

    def fake_write_json_report(_report):
        path = tmp_path / "diagnostic.json"
        path.write_text("{}\n", encoding="utf-8")
        return str(path)

    monkeypatch.setattr("app.main.write_json_report", fake_write_json_report)

    data = export_diag_json()

    assert data["status"] == "ok"
    assert data["format"] == "json"
    assert data["path"] == str(tmp_path / "diagnostic.json")


def test_post_diag_export_markdown_uses_isolated_output(tmp_path, monkeypatch):
    report = {
        "metadata": {"schema_version": APP_VERSION},
        "system": {},
        "network": {},
        "resources": {},
        "docker": {},
        "security": {},
    }
    monkeypatch.setattr("app.main.collect_network_diagnostic", lambda: report)

    def fake_write_markdown_report(_report):
        path = tmp_path / "diagnostic.md"
        path.write_text("# diagnostic\n", encoding="utf-8")
        return str(path)

    monkeypatch.setattr("app.main.write_markdown_report", fake_write_markdown_report)

    data = export_diag_markdown()

    assert data["status"] == "ok"
    assert data["format"] == "markdown"
    assert data["path"] == str(tmp_path / "diagnostic.md")
