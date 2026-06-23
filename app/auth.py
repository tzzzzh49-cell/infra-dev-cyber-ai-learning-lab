"""OIDC authentication and default-deny service-side authorization."""

from __future__ import annotations

import hashlib
import ipaddress
import math
import os
import time
from collections import deque
from collections.abc import Callable, Collection
from dataclasses import dataclass
from secrets import compare_digest
from threading import Lock
from typing import Annotated, Any
from urllib.parse import urlparse

import jwt
from cryptography.hazmat.primitives.asymmetric import ec, rsa
from fastapi import Depends, Header, HTTPException, Request, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import PyJWKClient
from jwt.exceptions import InvalidTokenError, PyJWKClientError

from app.logging_config import configure_logging

DIAG_TOKEN_HASH_ENV = "DIAG_ACCESS_TOKEN_HASH"
DIAG_TOKEN_HASH_FILE_ENV = "DIAG_ACCESS_TOKEN_HASH_FILE"
DIAG_PROTECTION_DISABLED_ENV = "DIAG_PROTECTION_DISABLED"
LOCAL_DEVELOPMENT_ENVS = {"local", "dev", "development", "test"}
LOCAL_TOKEN_ENVS = LOCAL_DEVELOPMENT_ENVS | {"lab"}
TRUE_VALUES = {"1", "true", "yes", "on"}

ALLOWED_ROLES = frozenset({"user", "admin", "partner"})
ALLOWED_PERMISSIONS = frozenset({"diagnostic:read", "diagnostic:export"})
ROLE_PERMISSIONS = {
    "user": frozenset(),
    "partner": frozenset({"diagnostic:read"}),
    "admin": ALLOWED_PERMISSIONS,
}
STRONG_JWT_ALGORITHMS = frozenset(
    {"RS256", "RS384", "RS512", "PS256", "PS384", "PS512", "ES256", "ES384", "ES512"}
)
MIN_RSA_KEY_SIZE = 2048
MIN_EC_KEY_SIZE = 256
MAX_TOKEN_LIFETIME_SECONDS = 900
JWT_CLOCK_SKEW_SECONDS = 30

DIAG_RATE_LIMIT = 5
DIAG_RATE_WINDOW_SECONDS = 60
AUTH_FAILURE_LIMIT = 5
AUTH_FAILURE_WINDOW_SECONDS = 300

RATE_LOCK = Lock()
DIAG_RATE_EVENTS: dict[str, deque[float]] = {}
AUTH_FAILURE_EVENTS: dict[str, deque[float]] = {}
JWKS_CLIENT_LOCK = Lock()
JWKS_CLIENTS: dict[str, PyJWKClient] = {}

logger = configure_logging(__name__)

oidc_bearer = HTTPBearer(
    auto_error=False,
    scheme_name="OIDC",
    description="JWT OIDC signé fourni dans l'en-tête Authorization Bearer.",
)


class OIDCConfigurationError(RuntimeError):
    """Raised when the trusted OIDC configuration is incomplete or unsafe."""


class AuthenticationRejected(ValueError):
    """Raised when an untrusted credential fails validation."""


@dataclass(frozen=True)
class Principal:
    """Validated identity used by service-side authorization."""

    subject: str
    audit_id: str
    roles: frozenset[str]
    mfa_verified: bool
    auth_method: str
    scopes: frozenset[str] = frozenset()

    @property
    def permissions(self) -> frozenset[str]:
        granted = set(self.scopes)
        for role in self.roles:
            granted.update(ROLE_PERMISSIONS.get(role, ()))
        return frozenset(granted)


def current_app_env() -> str:
    return os.environ.get("APP_ENV", "").strip().lower()


def env_flag_enabled(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in TRUE_VALUES


def local_diag_protection_disabled() -> bool:
    return (
        current_app_env() in LOCAL_DEVELOPMENT_ENVS
        and env_flag_enabled(DIAG_PROTECTION_DISABLED_ENV)
    )


def client_ip(request: Request) -> str:
    """Return a validated gateway client IP, or the direct peer address."""
    candidate = ""
    if current_app_env() == "vps":
        candidate = request.headers.get("X-Verified-Client-IP", "")
    if not candidate and request.client:
        candidate = request.client.host
    try:
        return str(ipaddress.ip_address(candidate))
    except ValueError:
        return "unknown"


def _prune(events: deque[float], cutoff: float) -> None:
    while events and events[0] <= cutoff:
        events.popleft()


def enforce_diag_rate_limit(key: str, now: float | None = None) -> None:
    """Allow at most five authorized diagnostic requests per minute."""
    current = time.monotonic() if now is None else now
    cutoff = current - DIAG_RATE_WINDOW_SECONDS

    with RATE_LOCK:
        for stored_key, events in list(DIAG_RATE_EVENTS.items()):
            _prune(events, cutoff)
            if not events:
                del DIAG_RATE_EVENTS[stored_key]

        events = DIAG_RATE_EVENTS.setdefault(key, deque())
        if len(events) >= DIAG_RATE_LIMIT:
            retry_after = max(
                1,
                math.ceil(events[0] + DIAG_RATE_WINDOW_SECONDS - current),
            )
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Diagnostic request quota exceeded.",
                headers={"Retry-After": str(retry_after)},
            )
        events.append(current)


def auth_retry_after(key: str, now: float | None = None) -> int:
    """Return a backoff duration after repeated authentication failures."""
    current = time.monotonic() if now is None else now
    cutoff = current - AUTH_FAILURE_WINDOW_SECONDS
    with RATE_LOCK:
        events = AUTH_FAILURE_EVENTS.get(key)
        if not events:
            return 0
        _prune(events, cutoff)
        if not events:
            del AUTH_FAILURE_EVENTS[key]
            return 0
        if len(events) < AUTH_FAILURE_LIMIT:
            return 0
        return max(1, math.ceil(events[0] + AUTH_FAILURE_WINDOW_SECONDS - current))


def record_auth_failure(key: str, now: float | None = None) -> None:
    current = time.monotonic() if now is None else now
    cutoff = current - AUTH_FAILURE_WINDOW_SECONDS
    with RATE_LOCK:
        events = AUTH_FAILURE_EVENTS.setdefault(key, deque())
        _prune(events, cutoff)
        events.append(current)


def clear_auth_failures(key: str) -> None:
    with RATE_LOCK:
        AUTH_FAILURE_EVENTS.pop(key, None)


def read_secret_file(path: str) -> str:
    try:
        with open(path, encoding="utf-8") as secret_file:
            return secret_file.read().strip()
    except OSError as exc:
        logger.error("Unable to read diagnostic token hash file: %s", exc)
        return ""


def configured_diag_token_hash() -> str:
    hash_file = os.environ.get(DIAG_TOKEN_HASH_FILE_ENV, "").strip()
    if hash_file:
        return read_secret_file(hash_file)
    return os.environ.get(DIAG_TOKEN_HASH_ENV, "").strip()


def diag_token_matches(provided_token: str, stored_hash: str) -> bool:
    value = stored_hash.strip()
    if value.startswith("sha256:"):
        value = value.removeprefix("sha256:")
    if len(value) != 64 or any(char not in "0123456789abcdefABCDEF" for char in value):
        return False
    provided_hash = hashlib.sha256(provided_token.encode("utf-8")).hexdigest()
    return compare_digest(provided_hash, value.lower())


def required_oidc_setting(name: str, *, https_url: bool = False) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise OIDCConfigurationError(f"{name} is required")
    if https_url:
        parsed = urlparse(value)
        if parsed.scheme != "https" or not parsed.netloc or parsed.username:
            raise OIDCConfigurationError(f"{name} must be an HTTPS URL")
    return value


def get_jwks_client(url: str) -> PyJWKClient:
    with JWKS_CLIENT_LOCK:
        client = JWKS_CLIENTS.get(url)
        if client is None:
            client = PyJWKClient(
                url,
                cache_keys=True,
                max_cached_keys=16,
                cache_jwk_set=True,
                lifespan=300,
                timeout=5,
            )
            JWKS_CLIENTS[url] = client
        return client


def validate_public_key(key: Any) -> None:
    if isinstance(key, rsa.RSAPublicKey):
        if key.key_size < MIN_RSA_KEY_SIZE:
            raise AuthenticationRejected("RSA signing key is too short")
        return
    if isinstance(key, ec.EllipticCurvePublicKey):
        if key.key_size < MIN_EC_KEY_SIZE:
            raise AuthenticationRejected("EC signing key is too short")
        return
    raise AuthenticationRejected("Unsupported JWT signing key type")


def claim_value(claims: dict[str, Any], path: str) -> Any:
    value: Any = claims
    for part in path.split("."):
        if not part or not isinstance(value, dict) or part not in value:
            return None
        value = value[part]
    return value


def validated_roles(claims: dict[str, Any]) -> frozenset[str]:
    claim_path = os.environ.get("OIDC_ROLES_CLAIM", "roles").strip() or "roles"
    raw_roles = claim_value(claims, claim_path)
    if isinstance(raw_roles, str):
        values = {raw_roles}
    elif isinstance(raw_roles, list) and all(
        isinstance(role, str) for role in raw_roles
    ):
        values = set(raw_roles)
    else:
        values = set()
    return frozenset(role for role in values if role in ALLOWED_ROLES)


def validated_scopes(claims: dict[str, Any]) -> frozenset[str]:
    """Keep only permissions explicitly supported by this API."""
    values: set[str] = set()
    for raw_scopes in (claims.get("scope"), claims.get("scp")):
        if isinstance(raw_scopes, str):
            values.update(raw_scopes.split())
        elif isinstance(raw_scopes, list) and all(
            isinstance(scope, str) for scope in raw_scopes
        ):
            values.update(raw_scopes)
    return frozenset(values.intersection(ALLOWED_PERMISSIONS))


def mfa_verified(claims: dict[str, Any]) -> bool:
    raw_amr = claims.get("amr", [])
    if isinstance(raw_amr, str):
        amr = {raw_amr}
    elif isinstance(raw_amr, list) and all(
        isinstance(method, str) for method in raw_amr
    ):
        amr = set(raw_amr)
    else:
        amr = set()
    if "mfa" in amr:
        return True
    accepted_acr = {
        value.strip()
        for value in os.environ.get("OIDC_MFA_ACR_VALUES", "").split(",")
        if value.strip()
    }
    acr = claims.get("acr")
    return bool(accepted_acr and isinstance(acr, str) and acr in accepted_acr)


def validate_oidc_token(token: str) -> Principal:
    """Validate issuer, signature, algorithm, key size, audience and lifetime."""
    issuer = required_oidc_setting("OIDC_ISSUER_URL", https_url=True)
    jwks_url = required_oidc_setting("OIDC_JWKS_URL", https_url=True)
    audience = required_oidc_setting("OIDC_AUDIENCE")

    try:
        header = jwt.get_unverified_header(token)
        algorithm = header.get("alg")
        if algorithm not in STRONG_JWT_ALGORITHMS:
            raise AuthenticationRejected("JWT algorithm is not allowed")
        if not header.get("kid"):
            raise AuthenticationRejected("JWT kid is required")

        signing_key = get_jwks_client(jwks_url).get_signing_key_from_jwt(token)
        if signing_key.algorithm_name and signing_key.algorithm_name != algorithm:
            raise AuthenticationRejected("JWT algorithm does not match its JWK")
        validate_public_key(signing_key.key)

        claims = jwt.decode(
            token,
            signing_key.key,
            algorithms=list(STRONG_JWT_ALGORITHMS),
            audience=audience,
            issuer=issuer,
            leeway=JWT_CLOCK_SKEW_SECONDS,
            options={"require": ["exp", "iat", "iss", "sub", "aud"]},
        )
    except AuthenticationRejected:
        raise
    except (InvalidTokenError, PyJWKClientError, ValueError, TypeError) as exc:
        raise AuthenticationRejected("JWT validation failed") from exc

    issued_at = claims["iat"]
    expires_at = claims["exp"]
    if (
        isinstance(issued_at, bool)
        or isinstance(expires_at, bool)
        or not isinstance(issued_at, (int, float))
        or not isinstance(expires_at, (int, float))
        or expires_at <= issued_at
        or expires_at - issued_at > MAX_TOKEN_LIFETIME_SECONDS
    ):
        raise AuthenticationRejected("JWT lifetime is invalid")

    subject = claims["sub"]
    if not isinstance(subject, str) or not subject or len(subject) > 255:
        raise AuthenticationRejected("JWT subject is invalid")

    roles = validated_roles(claims)
    audit_id = hashlib.sha256(f"{issuer}|{subject}".encode()).hexdigest()[:16]
    return Principal(
        subject=subject,
        audit_id=f"oidc:{audit_id}",
        roles=roles,
        mfa_verified=mfa_verified(claims),
        auth_method="oidc",
        scopes=validated_scopes(claims),
    )


def authenticate_local_token(token: str) -> Principal:
    if current_app_env() not in LOCAL_TOKEN_ENVS:
        raise AuthenticationRejected("Local tokens are disabled")
    expected_hash = configured_diag_token_hash()
    if not expected_hash:
        raise OIDCConfigurationError("Diagnostic token hash is required locally")
    if not diag_token_matches(token, expected_hash):
        raise AuthenticationRejected("Local token validation failed")
    return Principal(
        subject="local-lab",
        audit_id="local-lab",
        roles=frozenset({"admin"}),
        mfa_verified=False,
        auth_method="local-token",
    )


def authentication_failure(request: Request, key: str) -> None:
    record_auth_failure(key)
    request.state.auth_result = "failed"
    logger.warning("Authentication failed client_ip=%s", key)
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required.",
        headers={"WWW-Authenticate": "Bearer"},
    )


def authenticate_request(
    request: Request,
    credentials: Annotated[
        HTTPAuthorizationCredentials | None,
        Security(oidc_bearer),
    ] = None,
    x_diag_token: Annotated[str | None, Header(alias="X-Diag-Token")] = None,
) -> Principal:
    """Authenticate one request; OIDC is mandatory outside the local lab."""
    ip = client_ip(request)
    retry_after = auth_retry_after(ip)
    if retry_after:
        request.state.auth_result = "blocked"
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many authentication failures.",
            headers={"Retry-After": str(retry_after)},
        )

    if local_diag_protection_disabled():
        principal = Principal(
            subject="local-development",
            audit_id="local-development",
            roles=frozenset({"admin"}),
            mfa_verified=False,
            auth_method="disabled-locally",
        )
    else:
        token = credentials.credentials if credentials else x_diag_token
        if not token:
            authentication_failure(request, ip)
        try:
            if current_app_env() in LOCAL_TOKEN_ENVS and token.count(".") != 2:
                principal = authenticate_local_token(token)
            else:
                principal = validate_oidc_token(token)
        except OIDCConfigurationError:
            request.state.auth_result = "misconfigured"
            logger.error("Authentication configuration is incomplete.")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Authentication service is not configured.",
            ) from None
        except AuthenticationRejected:
            authentication_failure(request, ip)

    clear_auth_failures(ip)
    request.state.auth_identity = principal.audit_id
    request.state.auth_result = "success"
    return principal


def require_permissions(
    *required_permissions: str,
    require_mfa: bool = False,
) -> Callable[..., Principal]:
    """Require every named permission and optionally a verified second factor."""
    required = frozenset(required_permissions)
    if not required or not required.issubset(ALLOWED_PERMISSIONS):
        raise ValueError("Authorization requires explicit known permissions")

    def authorize(
        request: Request,
        principal: Annotated[Principal, Depends(authenticate_request)],
    ) -> Principal:
        if not required.issubset(principal.permissions):
            request.state.auth_result = "forbidden"
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions.",
            )
        if require_mfa and current_app_env() == "vps" and not principal.mfa_verified:
            request.state.auth_result = "mfa-required"
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Multi-factor authentication is required.",
            )

        enforce_diag_rate_limit(principal.audit_id)
        return principal

    return authorize


def authorize_resource_access(
    principal: Principal,
    *,
    permission: str,
    owner_subject: str,
    acl_subjects: Collection[str] = (),
) -> None:
    """Authorize using the persisted owner/ACL, never an owner sent by the client."""
    if permission not in ALLOWED_PERMISSIONS:
        raise ValueError("Resource authorization requires a known permission")
    if permission not in principal.permissions:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions.",
        )
    if not owner_subject or (
        principal.subject != owner_subject and principal.subject not in acl_subjects
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resource not found.",
        )
