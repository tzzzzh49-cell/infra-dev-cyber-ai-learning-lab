from app.main import diag, health, root, version


def test_root_returns_available_endpoints():
    data = root()

    assert data["message"] == "Mini API locale active"
    assert "/health" in data["endpoints"]
    assert "/version" in data["endpoints"]
    assert "/diag" in data["endpoints"]
    assert "/diag/export/json" in data["endpoints"]
    assert "/diag/export/markdown" in data["endpoints"]


def test_health_returns_ok_status():
    data = health()

    assert data["status"] == "ok"
    assert data["service"] == "lab-api"


def test_version_returns_app_version():
    data = version()

    assert data["app"] == "infra-dev-cyber-ai-learning-lab-api"
    assert data["version"] == "0.3.0"


def test_diag_returns_structured_diagnostic():
    data = diag()

    assert "metadata" in data
    assert "system" in data
    assert "network" in data
    assert "resources" in data
    assert "security" in data
