import hashlib

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.main import (
    APP_VERSION,
    DIAG_EXECUTION_LOCK,
    app,
    diag,
    export_diag_json,
    export_diag_markdown,
    health,
    require_diag_access,
    root,
    version,
)


@pytest.fixture(autouse=True)
def clear_diag_environment(monkeypatch):
    monkeypatch.delenv("APP_ENV", raising=False)
    monkeypatch.delenv("DIAG_ACCESS_TOKEN", raising=False)
    monkeypatch.delenv("DIAG_ACCESS_TOKEN_HASH", raising=False)
    monkeypatch.delenv("DIAG_ACCESS_TOKEN_HASH_FILE", raising=False)
    monkeypatch.delenv("DIAG_PROTECTION_DISABLED", raising=False)


def sample_report():
    return {
        "metadata": {"schema_version": APP_VERSION},
        "system": {},
        "network": {},
        "resources": {},
        "docker": {},
        "security": {},
    }


def route_methods(path):
    methods = set()
    for route in app.routes:
        if route.path == path:
            methods.update(route.methods or set())
    return methods


def route_dependencies(path):
    for route in app.routes:
        if route.path == path:
            return [
                dependency.dependency
                for dependency in getattr(route, "dependencies", [])
            ]
    return []


def sha256_token(token):
    return f"sha256:{hashlib.sha256(token.encode('utf-8')).hexdigest()}"


def disable_diag_protection_for_local_dev(monkeypatch):
    monkeypatch.setenv("APP_ENV", "local")
    monkeypatch.setenv("DIAG_PROTECTION_DISABLED", "true")


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


def test_diag_routes_require_access_dependency():
    sensitive_routes = (
        "/diag",
        "/diag/export/json",
        "/diag/export/markdown",
    )

    for path in sensitive_routes:
        assert require_diag_access in route_dependencies(path)


def test_root_registers_head_for_curl_i():
    assert "HEAD" in route_methods("/")


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


def test_http_routes_work_with_pinned_starlette():
    with TestClient(app) as client:
        assert client.get("/health").status_code == 200
        assert client.get("/diag").status_code == 503


def test_get_version_returns_app_version():
    assert version() == {
        "app": "infra-dev-cyber-ai-learning-lab-api",
        "version": APP_VERSION,
    }


def test_get_diag_returns_structured_diagnostic(monkeypatch):
    disable_diag_protection_for_local_dev(monkeypatch)
    monkeypatch.setattr("app.main.collect_network_diagnostic", sample_report)

    require_diag_access()
    data = diag()

    assert "metadata" in data
    assert "system" in data
    assert "network" in data
    assert "resources" in data
    assert "docker" in data
    assert "security" in data


def test_diag_rejects_concurrent_execution():
    DIAG_EXECUTION_LOCK.acquire()
    try:
        with pytest.raises(HTTPException) as exc:
            diag()
    finally:
        DIAG_EXECUTION_LOCK.release()

    assert exc.value.status_code == 429
    assert exc.value.headers == {"Retry-After": "1"}


def test_post_diag_export_json_uses_isolated_output(tmp_path, monkeypatch):
    disable_diag_protection_for_local_dev(monkeypatch)
    monkeypatch.setattr("app.main.collect_network_diagnostic", sample_report)

    def fake_write_json_report(_report):
        path = tmp_path / "diagnostic.json"
        path.write_text("{}\n", encoding="utf-8")
        return str(path)

    monkeypatch.setattr("app.main.write_json_report", fake_write_json_report)

    require_diag_access()
    data = export_diag_json()

    assert data["status"] == "ok"
    assert data["format"] == "json"
    assert data["path"] == str(tmp_path / "diagnostic.json")


def test_post_diag_export_markdown_uses_isolated_output(tmp_path, monkeypatch):
    disable_diag_protection_for_local_dev(monkeypatch)
    monkeypatch.setattr("app.main.collect_network_diagnostic", sample_report)

    def fake_write_markdown_report(_report):
        path = tmp_path / "diagnostic.md"
        path.write_text("# diagnostic\n", encoding="utf-8")
        return str(path)

    monkeypatch.setattr("app.main.write_markdown_report", fake_write_markdown_report)

    require_diag_access()
    data = export_diag_markdown()

    assert data["status"] == "ok"
    assert data["format"] == "markdown"
    assert data["path"] == str(tmp_path / "diagnostic.md")


def test_diag_requires_hash_by_default():
    with pytest.raises(HTTPException) as exc:
        require_diag_access()

    assert exc.value.status_code == 503


def test_diag_requires_hash_in_local_unless_explicitly_disabled(monkeypatch):
    monkeypatch.setenv("APP_ENV", "local")

    with pytest.raises(HTTPException) as exc:
        require_diag_access()

    assert exc.value.status_code == 503


def test_diag_ignores_legacy_plaintext_token_configuration(monkeypatch):
    monkeypatch.setenv("DIAG_ACCESS_TOKEN", "test-token")

    with pytest.raises(HTTPException) as exc:
        require_diag_access()

    assert exc.value.status_code == 503


def test_diag_allows_explicit_local_development_disable(monkeypatch):
    disable_diag_protection_for_local_dev(monkeypatch)
    monkeypatch.setattr("app.main.collect_network_diagnostic", sample_report)

    require_diag_access()


def test_diag_disable_is_ignored_in_vps(monkeypatch):
    monkeypatch.setenv("APP_ENV", "vps")
    monkeypatch.setenv("DIAG_PROTECTION_DISABLED", "true")

    with pytest.raises(HTTPException) as exc:
        require_diag_access()

    assert exc.value.status_code == 503


def test_diag_disable_is_ignored_in_default_lab(monkeypatch):
    monkeypatch.setenv("APP_ENV", "lab")
    monkeypatch.setenv("DIAG_PROTECTION_DISABLED", "true")

    with pytest.raises(HTTPException) as exc:
        require_diag_access()

    assert exc.value.status_code == 503


def test_diag_requires_token_when_hash_configured(monkeypatch):
    monkeypatch.setenv("DIAG_ACCESS_TOKEN_HASH", sha256_token("test-token"))

    with pytest.raises(HTTPException) as exc:
        require_diag_access()

    assert exc.value.status_code == 401


def test_diag_rejects_invalid_token(monkeypatch):
    monkeypatch.setenv("DIAG_ACCESS_TOKEN_HASH", sha256_token("test-token"))

    with pytest.raises(HTTPException) as exc:
        require_diag_access(authorization="Bearer wrong-token")

    assert exc.value.status_code == 401


def test_diag_accepts_bearer_token(monkeypatch):
    monkeypatch.setenv("DIAG_ACCESS_TOKEN_HASH", sha256_token("test-token"))
    monkeypatch.setattr("app.main.collect_network_diagnostic", sample_report)

    require_diag_access(authorization="Bearer test-token")
    data = diag()

    assert data["metadata"]["schema_version"] == APP_VERSION


def test_diag_rejects_bcrypt_hash(monkeypatch):
    monkeypatch.setenv("DIAG_ACCESS_TOKEN_HASH", "bcrypt:unsupported")

    with pytest.raises(HTTPException) as exc:
        require_diag_access(authorization="Bearer test-token")

    assert exc.value.status_code == 401


def test_diag_accepts_token_hash_from_secret_file(tmp_path, monkeypatch):
    hash_file = tmp_path / "diag-token-hash"
    hash_file.write_text(sha256_token("test-token"), encoding="utf-8")
    monkeypatch.setenv("DIAG_ACCESS_TOKEN_HASH_FILE", str(hash_file))
    monkeypatch.setattr("app.main.collect_network_diagnostic", sample_report)

    require_diag_access(authorization="Bearer test-token")


def test_diag_export_json_rejects_missing_token(monkeypatch):
    monkeypatch.setenv("DIAG_ACCESS_TOKEN_HASH", sha256_token("test-token"))

    with pytest.raises(HTTPException) as exc:
        require_diag_access()

    assert exc.value.status_code == 401


def test_diag_export_markdown_accepts_x_diag_token(
    tmp_path,
    monkeypatch,
):
    monkeypatch.setenv("DIAG_ACCESS_TOKEN_HASH", sha256_token("test-token"))
    monkeypatch.setattr("app.main.collect_network_diagnostic", sample_report)

    def fake_write_markdown_report(_report):
        path = tmp_path / "diagnostic.md"
        path.write_text("# diagnostic\n", encoding="utf-8")
        return str(path)

    monkeypatch.setattr("app.main.write_markdown_report", fake_write_markdown_report)

    require_diag_access(x_diag_token="test-token")
    data = export_diag_markdown()

    assert data["path"] == str(tmp_path / "diagnostic.md")
