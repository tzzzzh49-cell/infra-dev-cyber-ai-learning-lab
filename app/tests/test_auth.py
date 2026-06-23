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


def bearer(token):
    return HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)


def principal(*roles, mfa=False):
    return auth.Principal(
        subject="subject-a",
        audit_id="oidc:audit",
        roles=frozenset(roles),
        mfa_verified=mfa,
        auth_method="oidc",
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


def test_valid_oidc_token_checks_roles_and_mfa(rsa_key):
    token = signed_token(rsa_key, roles=["admin"], amr=["pwd", "mfa"])

    result = auth.validate_oidc_token(token)

    assert result.roles == frozenset({"admin"})
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
def test_rbac_denies_standard_user_on_admin_endpoints(monkeypatch, path):
    monkeypatch.setattr(auth, "validate_oidc_token", lambda _token: principal("user"))

    with TestClient(app) as client:
        response = client.post(
            path,
            headers={"Authorization": "Bearer signed.jwt.token"},
        )

    assert response.status_code == 403
    assert response.json() == {"detail": "Insufficient permissions."}


def test_rbac_requires_mfa_for_admin_in_vps():
    authorize = auth.require_roles("admin")
    request = make_request()

    with pytest.raises(HTTPException) as exc:
        authorize(request, principal("admin", mfa=False))

    assert exc.value.status_code == 403
    assert exc.value.detail == "Multi-factor authentication is required."


def test_rbac_allows_partner_read_but_not_admin_action():
    request = make_request()
    partner = principal("partner")

    assert auth.require_roles("partner", "admin")(request, partner) == partner
    with pytest.raises(HTTPException) as exc:
        auth.require_roles("admin")(request, partner)

    assert exc.value.status_code == 403


def test_rbac_defaults_to_deny_for_unknown_or_missing_roles():
    authorize = auth.require_roles("partner", "admin")

    for denied_roles in [(), ("unknown",), ("user",)]:
        with pytest.raises(HTTPException) as exc:
            authorize(make_request(), principal(*denied_roles))

        assert exc.value.status_code == 403


def test_rbac_allows_mfa_admin_on_admin_action():
    admin = principal("admin", mfa=True)

    assert auth.require_roles("admin")(make_request(), admin) == admin


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
