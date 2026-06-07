from app.main import diag, health, root, version


def test_root_returns_available_endpoints():
    data = root()

    assert data["message"] == "Mini API locale active"
    assert "/health" in data["endpoints"]
    assert "/version" in data["endpoints"]
    assert "/diag" in data["endpoints"]


def test_health_returns_ok_status():
    data = health()

    assert data["status"] == "ok"
    assert data["service"] == "lab-api"


def test_version_returns_app_version():
    data = version()

    assert data["app"] == "infra-dev-cyber-ai-learning-lab-api"
    assert data["version"] == "0.2.0"


def test_diag_returns_system_information():
    data = diag()

    assert "hostname" in data
    assert "platform" in data
    assert "platform_version" in data
    assert "python_version" in data
    assert "time_utc" in data
