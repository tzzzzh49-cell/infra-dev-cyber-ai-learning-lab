import hashlib

import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from fastapi.testclient import TestClient
from starlette.requests import Request

from app.auth import (
    AUTH_FAILURE_EVENTS,
    DIAG_RATE_EVENTS,
    authenticate_request,
    enforce_diag_rate_limit,
)
from app.main import (
    APP_VERSION,
    DIAG_EXECUTION_LOCK,
    app,
    diag,
    diag_export_access,
    diag_read_access,
    diagnostic_api_view,
    export_diag_json,
    export_diag_markdown,
    health,
    root,
    version,
)


@pytest.fixture(autouse=True)
def clear_diag_environment(monkeypatch):
    monkeypatch.setenv("APP_ENV", "lab")
    monkeypatch.delenv("DIAG_ACCESS_TOKEN", raising=False)
    monkeypatch.delenv("DIAG_ACCESS_TOKEN_HASH", raising=False)
    monkeypatch.delenv("DIAG_ACCESS_TOKEN_HASH_FILE", raising=False)
    monkeypatch.delenv("DIAG_PROTECTION_DISABLED", raising=False)
    DIAG_RATE_EVENTS.clear()
    AUTH_FAILURE_EVENTS.clear()


def command_result():
    return {
        "available": True,
        "returncode": 0,
        "stdout": "sensitive raw output",
        "stderr": "",
        "timed_out": False,
        "duration_seconds": 0.01,
        "error_type": "",
    }


def sample_report():
    return {
        "metadata": {
            "schema_version": APP_VERSION,
            "generated_at_utc": "2026-06-23T00:00:00+00:00",
            "mode": "read-only",
            "command_timeout_seconds": 3.0,
            "private_metadata": "must not leave the API",
        },
        "system": {"hostname": "private-host"},
        "network": {
            "interfaces": command_result(),
            "routes": command_result(),
            "dns": {"resolver_commands": {"selected": command_result()}},
            "ports": command_result(),
        },
        "resources": {
            "disk": command_result(),
            "memory": command_result(),
        },
        "docker": command_result(),
        "security": {
            "read_only": True,
            "destructive_commands_used": False,
        },
    }


def make_request(headers=None, client="127.0.0.1"):
    raw_headers = [
        (name.lower().encode("ascii"), value.encode("ascii"))
        for name, value in (headers or {}).items()
    ]
    return Request({"type": "http", "headers": raw_headers, "client": (client, 1)})


def bearer(token):
    return HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)


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
    assert diag_read_access in route_dependencies("/diag")
    assert diag_export_access in route_dependencies("/diag/export/json")
    assert diag_export_access in route_dependencies("/diag/export/markdown")


def test_openapi_declares_bearer_security():
    schema = app.openapi()

    assert "OIDC" in schema["components"]["securitySchemes"]
    assert {"OIDC": []} in schema["paths"]["/diag"]["get"]["security"]


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
        response = client.get("/diag")

    assert response.status_code == 401
    assert response.headers["cache-control"] == "no-store"
    assert len(response.headers["x-request-id"]) == 32


def test_get_version_returns_app_version():
    assert version() == {
        "app": "infra-dev-cyber-ai-learning-lab-api",
        "version": APP_VERSION,
    }


def test_get_diag_returns_structured_diagnostic(monkeypatch):
    disable_diag_protection_for_local_dev(monkeypatch)
    monkeypatch.setattr("app.main.collect_network_diagnostic", sample_report)

    authenticate_request(make_request())
    data = diag()

    assert "metadata" in data
    assert "checks" in data
    assert "security" in data
    assert "system" not in data
    assert "stdout" not in str(data)


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

    authenticate_request(make_request())
    data = export_diag_json()

    assert data["status"] == "ok"
    assert data["format"] == "json"
    assert data["report_id"] == "diagnostic"


def test_post_diag_export_markdown_uses_isolated_output(tmp_path, monkeypatch):
    disable_diag_protection_for_local_dev(monkeypatch)
    monkeypatch.setattr("app.main.collect_network_diagnostic", sample_report)

    def fake_write_markdown_report(_report):
        path = tmp_path / "diagnostic.md"
        path.write_text("# diagnostic\n", encoding="utf-8")
        return str(path)

    monkeypatch.setattr("app.main.write_markdown_report", fake_write_markdown_report)

    authenticate_request(make_request())
    data = export_diag_markdown()

    assert data["status"] == "ok"
    assert data["format"] == "markdown"
    assert data["report_id"] == "diagnostic"


def test_diag_requires_hash_by_default():
    with pytest.raises(HTTPException) as exc:
        authenticate_request(make_request(), x_diag_token="test-token")

    assert exc.value.status_code == 503


def test_diag_requires_hash_in_local_unless_explicitly_disabled(monkeypatch):
    monkeypatch.setenv("APP_ENV", "local")

    with pytest.raises(HTTPException) as exc:
        authenticate_request(make_request(), x_diag_token="test-token")

    assert exc.value.status_code == 503


def test_diag_ignores_legacy_plaintext_token_configuration(monkeypatch):
    monkeypatch.setenv("DIAG_ACCESS_TOKEN", "test-token")

    with pytest.raises(HTTPException) as exc:
        authenticate_request(make_request(), x_diag_token="test-token")

    assert exc.value.status_code == 503


def test_diag_allows_explicit_local_development_disable(monkeypatch):
    disable_diag_protection_for_local_dev(monkeypatch)
    monkeypatch.setattr("app.main.collect_network_diagnostic", sample_report)

    authenticate_request(make_request())


def test_diag_disable_is_ignored_in_vps(monkeypatch):
    monkeypatch.setenv("APP_ENV", "vps")
    monkeypatch.setenv("DIAG_PROTECTION_DISABLED", "true")

    with pytest.raises(HTTPException) as exc:
        authenticate_request(make_request())

    assert exc.value.status_code == 401


def test_diag_disable_is_ignored_in_default_lab(monkeypatch):
    monkeypatch.setenv("APP_ENV", "lab")
    monkeypatch.setenv("DIAG_PROTECTION_DISABLED", "true")

    with pytest.raises(HTTPException) as exc:
        authenticate_request(make_request())

    assert exc.value.status_code == 401


def test_diag_requires_token_when_hash_configured(monkeypatch):
    monkeypatch.setenv("DIAG_ACCESS_TOKEN_HASH", sha256_token("test-token"))

    with pytest.raises(HTTPException) as exc:
        authenticate_request(make_request())

    assert exc.value.status_code == 401


def test_diag_rejects_invalid_token(monkeypatch):
    monkeypatch.setenv("DIAG_ACCESS_TOKEN_HASH", sha256_token("test-token"))

    with pytest.raises(HTTPException) as exc:
        authenticate_request(make_request(), credentials=bearer("wrong-token"))

    assert exc.value.status_code == 401


def test_diag_accepts_bearer_token(monkeypatch):
    monkeypatch.setenv("DIAG_ACCESS_TOKEN_HASH", sha256_token("test-token"))
    monkeypatch.setattr("app.main.collect_network_diagnostic", sample_report)

    authenticate_request(make_request(), credentials=bearer("test-token"))
    data = diag()

    assert data["metadata"]["schema_version"] == APP_VERSION


def test_diag_rejects_bcrypt_hash(monkeypatch):
    monkeypatch.setenv("DIAG_ACCESS_TOKEN_HASH", "bcrypt:unsupported")

    with pytest.raises(HTTPException) as exc:
        authenticate_request(make_request(), credentials=bearer("test-token"))

    assert exc.value.status_code == 401


def test_diag_accepts_token_hash_from_secret_file(tmp_path, monkeypatch):
    hash_file = tmp_path / "diag-token-hash"
    hash_file.write_text(sha256_token("test-token"), encoding="utf-8")
    monkeypatch.setenv("DIAG_ACCESS_TOKEN_HASH_FILE", str(hash_file))
    monkeypatch.setattr("app.main.collect_network_diagnostic", sample_report)

    authenticate_request(make_request(), credentials=bearer("test-token"))


def test_diag_export_json_rejects_missing_token(monkeypatch):
    monkeypatch.setenv("DIAG_ACCESS_TOKEN_HASH", sha256_token("test-token"))

    with pytest.raises(HTTPException) as exc:
        authenticate_request(make_request())

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

    request = make_request()
    principal = authenticate_request(request, x_diag_token="test-token")
    data = export_diag_markdown()

    assert principal.auth_method == "local-token"
    assert request.state.auth_identity == "local-lab"
    assert data["report_id"] == "diagnostic"


def test_diag_rate_limit_rejects_sixth_request():
    for second in range(5):
        enforce_diag_rate_limit("identity:test", now=float(second))

    with pytest.raises(HTTPException) as exc:
        enforce_diag_rate_limit("identity:test", now=5.0)

    assert exc.value.status_code == 429
    assert exc.value.headers == {"Retry-After": "55"}


def test_diagnostic_api_view_removes_raw_and_identifying_data():
    data = diagnostic_api_view(sample_report())

    assert "system" not in data
    assert "private-host" not in str(data)
    assert "private_metadata" not in str(data)
    assert "sensitive raw output" not in str(data)


def test_unhandled_http_error_returns_generic_response(monkeypatch):
    disable_diag_protection_for_local_dev(monkeypatch)

    def fail_diagnostic():
        raise RuntimeError("internal diagnostic detail")

    monkeypatch.setattr("app.main.collect_network_diagnostic", fail_diagnostic)

    with TestClient(app) as client:
        response = client.get("/diag")

    assert response.status_code == 500
    assert response.json()["detail"] == "Internal server error."
    assert "internal diagnostic detail" not in response.text
    assert response.headers["cache-control"] == "no-store"
