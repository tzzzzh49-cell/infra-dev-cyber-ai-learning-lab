from fastapi.testclient import TestClient

from app.main import APP_VERSION, app

client = TestClient(app)


def test_get_root_returns_available_endpoints():
    response = client.get("/")

    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "Mini API locale active"
    assert "/health" in data["endpoints"]
    assert "/version" in data["endpoints"]
    assert "/diag" in data["endpoints"]
    assert "/diag/export/json" in data["endpoints"]
    assert "/diag/export/markdown" in data["endpoints"]


def test_get_health_returns_ok_status():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "lab-api"}


def test_get_version_returns_app_version():
    response = client.get("/version")

    assert response.status_code == 200
    assert response.json() == {
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

    response = client.get("/diag")

    assert response.status_code == 200
    data = response.json()
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

    response = client.post("/diag/export/json")

    assert response.status_code == 200
    data = response.json()
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

    response = client.post("/diag/export/markdown")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["format"] == "markdown"
    assert data["path"] == str(tmp_path / "diagnostic.md")
