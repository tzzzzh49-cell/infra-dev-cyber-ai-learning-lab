import asyncio

import httpx
import pytest

from app.diagnostics import SCHEMA_VERSION
from app.main import APP_VERSION, app


class ASGITestClient:
    def request(self, method, path, **kwargs):
        async def call_app():
            transport = httpx.ASGITransport(app=app)
            async with httpx.AsyncClient(
                transport=transport,
                base_url="http://testserver",
            ) as client:
                return await client.request(method, path, **kwargs)

        return asyncio.run(call_app())

    def get(self, path, **kwargs):
        return self.request("GET", path, **kwargs)

    def post(self, path, **kwargs):
        return self.request("POST", path, **kwargs)


@pytest.fixture
def client(monkeypatch):
    monkeypatch.delenv("APP_ENV", raising=False)
    monkeypatch.delenv("DIAG_ACCESS_TOKEN", raising=False)
    monkeypatch.delenv("DIAG_ACCESS_TOKEN_SHA256", raising=False)
    return ASGITestClient()


def sample_report():
    return {
        "metadata": {"schema_version": SCHEMA_VERSION},
        "system": {},
        "network": {},
        "resources": {},
        "docker": {},
        "security": {},
    }


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


def test_get_root_returns_available_endpoints(client):
    response = client.get("/")

    assert response.status_code == 200
    data = response.json()

    assert data["message"] == "Mini API locale active"
    assert "/health" in data["endpoints"]
    assert "/version" in data["endpoints"]
    assert "/diag" in data["endpoints"]
    assert "/diag/export/json" in data["endpoints"]
    assert "/diag/export/markdown" in data["endpoints"]


def test_get_health_returns_ok_status(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "lab-api"}


def test_get_version_returns_app_version(client):
    response = client.get("/version")

    assert response.status_code == 200
    assert response.json() == {
        "app": "infra-dev-cyber-ai-learning-lab-api",
        "version": APP_VERSION,
    }


def test_get_diag_returns_structured_diagnostic(client, monkeypatch):
    monkeypatch.setattr("app.main.collect_network_diagnostic", sample_report)

    response = client.get("/diag")

    assert response.status_code == 200
    data = response.json()
    assert "metadata" in data
    assert "system" in data
    assert "network" in data
    assert "resources" in data
    assert "docker" in data
    assert "security" in data


def test_post_diag_export_json_uses_isolated_output(client, tmp_path, monkeypatch):
    monkeypatch.setattr("app.main.collect_network_diagnostic", sample_report)

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


def test_post_diag_export_markdown_uses_isolated_output(client, tmp_path, monkeypatch):
    monkeypatch.setattr("app.main.collect_network_diagnostic", sample_report)

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


def test_diag_is_blocked_in_vps_mode_without_configured_token(client, monkeypatch):
    monkeypatch.setenv("APP_ENV", "vps")

    response = client.get("/diag")

    assert response.status_code == 503


def test_diag_requires_token_when_configured(client, monkeypatch):
    monkeypatch.setenv("DIAG_ACCESS_TOKEN", "test-token")

    response = client.get("/diag")

    assert response.status_code == 401


def test_diag_rejects_invalid_token(client, monkeypatch):
    monkeypatch.setenv("APP_ENV", "vps")
    monkeypatch.setenv("DIAG_ACCESS_TOKEN", "test-token")

    response = client.get("/diag", headers={"Authorization": "Bearer wrong-token"})

    assert response.status_code == 401


def test_diag_accepts_bearer_token(client, monkeypatch):
    monkeypatch.setenv("APP_ENV", "vps")
    monkeypatch.setenv("DIAG_ACCESS_TOKEN", "test-token")
    monkeypatch.setattr("app.main.collect_network_diagnostic", sample_report)

    response = client.get("/diag", headers={"Authorization": "Bearer test-token"})

    assert response.status_code == 200
    assert response.json()["metadata"]["schema_version"] == SCHEMA_VERSION


def test_diag_accepts_hashed_token(client, monkeypatch):
    monkeypatch.setenv("APP_ENV", "vps")
    monkeypatch.setenv(
        "DIAG_ACCESS_TOKEN_SHA256",
        "4c5dc9b7708905f77f5e5d16316b5dfb425e68cb326dcd55a860e90a7707031e",
    )
    monkeypatch.setattr("app.main.collect_network_diagnostic", sample_report)

    response = client.get("/diag", headers={"Authorization": "Bearer test-token"})

    assert response.status_code == 200
    assert response.json()["metadata"]["schema_version"] == SCHEMA_VERSION


def test_diag_export_json_rejects_missing_token(client, monkeypatch):
    monkeypatch.setenv("APP_ENV", "vps")
    monkeypatch.setenv("DIAG_ACCESS_TOKEN", "test-token")

    response = client.post("/diag/export/json")

    assert response.status_code == 401


def test_diag_export_markdown_accepts_x_diag_token(
    client,
    tmp_path,
    monkeypatch,
):
    monkeypatch.setenv("APP_ENV", "vps")
    monkeypatch.setenv("DIAG_ACCESS_TOKEN", "test-token")
    monkeypatch.setattr("app.main.collect_network_diagnostic", sample_report)

    def fake_write_markdown_report(_report):
        path = tmp_path / "diagnostic.md"
        path.write_text("# diagnostic\n", encoding="utf-8")
        return str(path)

    monkeypatch.setattr("app.main.write_markdown_report", fake_write_markdown_report)

    response = client.post(
        "/diag/export/markdown",
        headers={"X-Diag-Token": "test-token"},
    )

    assert response.status_code == 200
    assert response.json()["path"] == str(tmp_path / "diagnostic.md")
