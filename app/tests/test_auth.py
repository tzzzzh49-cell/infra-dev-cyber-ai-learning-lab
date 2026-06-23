import time
from types import SimpleNamespace

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from fastapi.testclient import TestClient
from starlette.requests import Request

from app import auth
from app.main import app

ISSUER = "https://issuer.example.test"
JWKS_URL = "https://issuer.example.test/jwks"
AUDIENCE = "lab-api"


def make_request(client="192.0.2.10"):
    return Request({"type": "http", "headers": [], "client": (client, 1)})


def make_forwarded_request(peer, verified_ip):
    return Request(
        {
            "type": "http",
            "headers": [
                (b"x-verified-client-ip", verified_ip.encode("ascii")),
            ],
            "client": (peer, 1),
        }
    )


def bearer(token):
    return HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)


def principal(*roles, mfa=False, subject="subject-a", scopes=()):
    return auth.Principal(
        subject=subject,
        audit_id="oidc:audit",
        roles=frozenset(roles),
        mfa_verified=mfa,
        auth_method="oidc",
        scopes=frozenset(scopes),
    )


def signed_token(private_key, **claim_overrides):
    now = int(time.time())
    claims = {
        "iss": ISSUER,
        "sub": "subject-a",
        "aud": AUDIENCE,
        "iat": now,
        "exp": now + 300,
        "roles": ["user"],
        "amr": ["pwd"],
    }
    claims.update(claim_overrides)
    return jwt.encode(
        claims,
        private_key,
        algorithm="RS256",
        headers={"kid": "test-key"},
    )


@pytest.fixture
def rsa_key():
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


@pytest.fixture(autouse=True)
def oidc_environment(monkeypatch, rsa_key):
    monkeypatch.setenv("APP_ENV", "vps")
    monkeypatch.setenv("OIDC_ISSUER_URL", ISSUER)
    monkeypatch.setenv("OIDC_JWKS_URL", JWKS_URL)
    monkeypatch.setenv("OIDC_AUDIENCE", AUDIENCE)
    monkeypatch.setenv("OIDC_ROLES_CLAIM", "roles")
    monkeypatch.delenv("OIDC_MFA_ACR_VALUES", raising=False)
    monkeypatch.delenv("TRUSTED_PROXY_CIDRS", raising=False)
    auth.AUTH_FAILURE_EVENTS.clear()
    auth.DIAG_RATE_EVENTS.clear()
    fake_key = SimpleNamespace(
        key=rsa_key.public_key(),
        algorithm_name="RS256",
    )
    monkeypatch.setattr(
        auth,
        "get_jwks_client",
        lambda _url: SimpleNamespace(get_signing_key_from_jwt=lambda _token: fake_key),
    )


def test_client_ip_trusts_only_the_configured_proxy(monkeypatch):
    monkeypatch.setenv("TRUSTED_PROXY_CIDRS", "172.30.0.2/32")

    assert auth.client_ip(make_forwarded_request("172.30.0.2", "198.51.100.7")) == (
        "198.51.100.7"
    )
    assert auth.client_ip(make_forwarded_request("172.30.0.9", "198.51.100.7")) == (
        "172.30.0.9"
    )


def test_valid_oidc_token_checks_roles_and_mfa(rsa_key):
    token = signed_token(
        rsa_key,
        roles=["admin"],
        scope="diagnostic:read unknown:scope",
        amr=["pwd", "mfa"],
    )

    result = auth.validate_oidc_token(token)

    assert result.roles == frozenset({"admin"})
    assert result.scopes == frozenset({"diagnostic:read"})
    assert result.permissions == auth.ALLOWED_PERMISSIONS
    assert result.mfa_verified is True
    assert result.audit_id.startswith("oidc:")


@pytest.mark.parametrize(
    "overrides",
    [
        {"iss": "https://attacker.example.test"},
        {"exp": int(time.time()) - 120},
        {"exp": int(time.time()) + 1800},
    ],
)
def test_oidc_rejects_wrong_issuer_expired_or_long_lived_tokens(rsa_key, overrides):
    token = signed_token(rsa_key, **overrides)

    with pytest.raises(auth.AuthenticationRejected):
        auth.validate_oidc_token(token)


def test_oidc_rejects_invalid_signature(rsa_key):
    other_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    token = signed_token(other_key)

    with pytest.raises(auth.AuthenticationRejected):
        auth.validate_oidc_token(token)


@pytest.mark.parametrize("algorithm", ["none", "HS256"])
def test_oidc_rejects_none_and_symmetric_algorithms(algorithm):
    key = "" if algorithm == "none" else "not-a-public-key"
    token = jwt.encode(
        {
            "iss": ISSUER,
            "sub": "subject-a",
            "aud": AUDIENCE,
            "iat": int(time.time()),
            "exp": int(time.time()) + 300,
        },
        key,
        algorithm=algorithm,
        headers={"kid": "test-key"},
    )

    with pytest.raises(auth.AuthenticationRejected):
        auth.validate_oidc_token(token)


def test_oidc_rejects_short_rsa_key(monkeypatch):
    short_key = rsa.generate_private_key(public_exponent=65537, key_size=1024)
    fake_key = SimpleNamespace(
        key=short_key.public_key(),
        algorithm_name="RS256",
    )
    monkeypatch.setattr(
        auth,
        "get_jwks_client",
        lambda _url: SimpleNamespace(get_signing_key_from_jwt=lambda _token: fake_key),
    )

    with pytest.raises(auth.AuthenticationRejected):
        auth.validate_oidc_token(signed_token(short_key))


@pytest.mark.parametrize(
    "path",
    ["/diag/export/json", "/diag/export/markdown"],
)
def test_permission_denies_standard_user_on_export_endpoints(monkeypatch, path):
    monkeypatch.setattr(auth, "validate_oidc_token", lambda _token: principal("user"))

    with TestClient(app) as client:
        response = client.post(
            path,
            headers={"Authorization": "Bearer signed.jwt.token"},
        )

    assert response.status_code == 403
    assert response.json() == {"detail": "Insufficient permissions."}


def test_verified_scope_allows_http_diagnostic_read(monkeypatch):
    monkeypatch.setattr(
        auth,
        "validate_oidc_token",
        lambda _token: principal("user", scopes={"diagnostic:read"}),
    )
    monkeypatch.setattr("app.main.collect_diagnostic_serialized", lambda: {})
    monkeypatch.setattr(
        "app.main.diagnostic_api_view",
        lambda _report: {"status": "ok"},
    )

    with TestClient(app) as client:
        response = client.get(
            "/diag",
            headers={"Authorization": "Bearer signed.jwt.token"},
        )

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.parametrize(
    ("path", "writer"),
    [
        ("/diag/export/json", "write_json_report"),
        ("/diag/export/markdown", "write_markdown_report"),
    ],
)
def test_mfa_admin_can_export(monkeypatch, path, writer):
    monkeypatch.setattr(
        auth,
        "validate_oidc_token",
        lambda _token: principal("admin", mfa=True),
    )
    monkeypatch.setattr("app.main.collect_diagnostic_serialized", lambda: {})
    monkeypatch.setattr(f"app.main.{writer}", lambda _report: "/tmp/diagnostic")

    with TestClient(app) as client:
        response = client.post(
            path,
            headers={"Authorization": "Bearer signed.jwt.token"},
        )

    assert response.status_code == 200
    assert response.json()["report_id"] == "diagnostic"


def test_permission_requires_mfa_for_critical_action_in_vps():
    authorize = auth.require_permissions("diagnostic:export", require_mfa=True)
    request = make_request()

    with pytest.raises(HTTPException) as exc:
        authorize(request, principal("admin", mfa=False))

    assert exc.value.status_code == 403
    assert exc.value.detail == "Multi-factor authentication is required."


def test_permission_allows_mapped_role_or_verified_scope():
    authorize = auth.require_permissions("diagnostic:read")

    partner = principal("partner")
    scoped_user = principal("user", scopes={"diagnostic:read"})

    assert authorize(make_request(), partner) == partner
    assert authorize(make_request(), scoped_user) == scoped_user


def test_permission_defaults_to_deny_without_explicit_grant():
    authorize = auth.require_permissions("diagnostic:export")

    for denied in (principal(), principal("user"), principal("partner")):
        with pytest.raises(HTTPException) as exc:
            authorize(make_request(), denied)

        assert exc.value.status_code == 403


def test_malformed_mfa_claims_fail_closed(rsa_key, monkeypatch):
    monkeypatch.setenv("OIDC_MFA_ACR_VALUES", "trusted-acr")
    token = signed_token(rsa_key, roles=["admin"], amr=123, acr=[])

    assert auth.validate_oidc_token(token).mfa_verified is False


def test_resource_access_allows_owner_or_server_side_acl():
    owner = principal("partner", subject="owner-a")
    acl_member = principal("partner", subject="member-b")

    auth.authorize_resource_access(
        owner,
        permission="diagnostic:read",
        owner_subject="owner-a",
    )
    auth.authorize_resource_access(
        acl_member,
        permission="diagnostic:read",
        owner_subject="owner-a",
        acl_subjects={"member-b"},
    )


def test_resource_access_hides_other_owners_and_denies_missing_permission():
    with pytest.raises(HTTPException) as exc:
        auth.authorize_resource_access(
            principal("partner", subject="attacker"),
            permission="diagnostic:read",
            owner_subject="owner-a",
        )
    assert exc.value.status_code == 404

    with pytest.raises(HTTPException) as exc:
        auth.authorize_resource_access(
            principal("user", subject="owner-a"),
            permission="diagnostic:read",
            owner_subject="owner-a",
        )
    assert exc.value.status_code == 403


def test_repeated_authentication_failures_are_blocked():
    for _attempt in range(auth.AUTH_FAILURE_LIMIT):
        with pytest.raises(HTTPException) as exc:
            auth.authenticate_request(make_request())
        assert exc.value.status_code == 401

    with pytest.raises(HTTPException) as exc:
        auth.authenticate_request(make_request())

    assert exc.value.status_code == 429
    assert int(exc.value.headers["Retry-After"]) > 0


def test_vps_refuses_local_shared_token(monkeypatch):
    monkeypatch.setenv("DIAG_ACCESS_TOKEN_HASH", "0" * 64)

    with pytest.raises(HTTPException) as exc:
        auth.authenticate_request(
            make_request(),
            credentials=bearer("local-token"),
        )

    assert exc.value.status_code == 401
