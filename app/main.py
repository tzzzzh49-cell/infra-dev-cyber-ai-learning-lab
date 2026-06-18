import hashlib
import os
from secrets import compare_digest
from typing import Annotated

try:
    import bcrypt
except ImportError:  # pragma: no cover - exercised only without optional package
    bcrypt = None

from fastapi import Depends, FastAPI, Header, HTTPException, status

from app.diagnostics import (
    collect_network_diagnostic,
    write_json_report,
    write_markdown_report,
)
from app.logging_config import configure_logging

APP_VERSION = "0.3.2"
DIAG_TOKEN_HASH_ENV = "DIAG_ACCESS_TOKEN_HASH"
DIAG_TOKEN_HASH_FILE_ENV = "DIAG_ACCESS_TOKEN_HASH_FILE"
DIAG_PROTECTION_DISABLED_ENV = "DIAG_PROTECTION_DISABLED"
LOCAL_DEVELOPMENT_ENVS = {"local", "lab", "dev", "development", "test"}
TRUE_VALUES = {"1", "true", "yes", "on"}
BCRYPT_PREFIXES = ("$2a$", "$2b$", "$2y$")

logger = configure_logging(__name__)

app = FastAPI(
    title="Infra Dev Cyber AI Learning Lab API",
    description="Mini API locale pour apprendre le DevOps, Docker et les diagnostics.",
    version=APP_VERSION,
)


def env_flag_enabled(name: str) -> bool:
    """Return true when an environment flag is explicitly enabled."""
    return os.environ.get(name, "").strip().lower() in TRUE_VALUES


def current_app_env() -> str:
    """Return the normalized application environment name."""
    return os.environ.get("APP_ENV", "").strip().lower()


def diag_protection_enabled() -> bool:
    """Return true unless diagnostics are explicitly opened for local development."""
    app_env = current_app_env()
    protection_disabled = env_flag_enabled(DIAG_PROTECTION_DISABLED_ENV)

    if protection_disabled and app_env in LOCAL_DEVELOPMENT_ENVS:
        logger.warning("Diagnostic protection disabled for local development.")
        return False

    if protection_disabled:
        logger.warning(
            "Ignoring %s outside local development.",
            DIAG_PROTECTION_DISABLED_ENV,
        )

    return True


def read_secret_file(path: str) -> str:
    """Read a secret value from a file mounted by a secrets manager."""
    try:
        with open(path, encoding="utf-8") as secret_file:
            return secret_file.read().strip()
    except OSError as exc:
        logger.error("Unable to read diagnostic token hash file: %s", exc)
        return ""


def configured_diag_token_hash() -> str:
    """Return the configured diagnostic token hash from env or a secret file."""
    hash_file = os.environ.get(DIAG_TOKEN_HASH_FILE_ENV, "").strip()
    if hash_file:
        return read_secret_file(hash_file)
    return os.environ.get(DIAG_TOKEN_HASH_ENV, "").strip()


def sha256_token_hash(token: str) -> str:
    """Hash a provided diagnostic token with SHA-256."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def parse_stored_token_hash(stored_hash: str) -> tuple[str, str]:
    """Return the hash algorithm and normalized value from configuration."""
    value = stored_hash.strip()
    if value.startswith("sha256:"):
        return "sha256", value.removeprefix("sha256:").lower()
    if len(value) == 64 and all(char in "0123456789abcdefABCDEF" for char in value):
        return "sha256", value.lower()
    if value.startswith("bcrypt:"):
        return "bcrypt", value.removeprefix("bcrypt:")
    if value.startswith(BCRYPT_PREFIXES):
        return "bcrypt", value
    return "unsupported", value


def diag_token_matches(provided_token: str, stored_hash: str) -> bool:
    """Compare a provided token with a stored SHA-256 or bcrypt hash."""
    algorithm, expected_hash = parse_stored_token_hash(stored_hash)

    if algorithm == "sha256":
        provided_hash = sha256_token_hash(provided_token)
        return compare_digest(provided_hash, expected_hash)

    if algorithm == "bcrypt":
        if bcrypt is None:
            logger.error("bcrypt token hash configured but bcrypt is not installed.")
            return False
        try:
            return bool(
                bcrypt.checkpw(
                    provided_token.encode("utf-8"),
                    expected_hash.encode("utf-8"),
                )
            )
        except ValueError as exc:
            logger.error("Invalid bcrypt diagnostic token hash: %s", exc)
            return False

    logger.error("Unsupported diagnostic token hash format configured.")
    return False


def require_diag_access(
    authorization: Annotated[str | None, Header()] = None,
    x_diag_token: Annotated[str | None, Header(alias="X-Diag-Token")] = None,
) -> None:
    """Require a valid diagnostic token unless local development disabled protection."""
    if not diag_protection_enabled():
        return

    expected_hash = configured_diag_token_hash()
    if not expected_hash:
        logger.error("Diagnostic access denied: no token hash configured.")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Diagnostic access token hash is required.",
        )

    provided_token = x_diag_token
    if authorization:
        scheme, _, token = authorization.partition(" ")
        if scheme.lower() == "bearer" and token:
            provided_token = token

    if not provided_token or not diag_token_matches(provided_token, expected_hash):
        logger.warning("Diagnostic authentication failed.")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Diagnostic authentication required.",
            headers={"WWW-Authenticate": "Bearer"},
        )


@app.get("/")
def root():
    """Return the public API entrypoint and available endpoints."""
    return {
        "message": "Mini API locale active",
        "endpoints": [
            "/health",
            "/version",
            "/diag",
            "/diag/export/json",
            "/diag/export/markdown",
        ],
    }


@app.head("/")
def root_head():
    return None


@app.get("/health")
def health():
    """Return a minimal health status."""
    return {
        "status": "ok",
        "service": "lab-api",
    }


@app.get("/version")
def version():
    """Return the application name and version."""
    return {
        "app": "infra-dev-cyber-ai-learning-lab-api",
        "version": APP_VERSION,
    }


@app.get("/diag", dependencies=[Depends(require_diag_access)])
def diag():
    """Return a read-only diagnostic report."""
    return collect_network_diagnostic()


@app.post("/diag/export/json", dependencies=[Depends(require_diag_access)])
def export_diag_json():
    """Write a read-only diagnostic report as JSON."""
    report = collect_network_diagnostic()
    path = write_json_report(report)
    return {
        "status": "ok",
        "format": "json",
        "path": path,
    }


@app.post("/diag/export/markdown", dependencies=[Depends(require_diag_access)])
def export_diag_markdown():
    """Write a read-only diagnostic report as Markdown."""
    report = collect_network_diagnostic()
    path = write_markdown_report(report)
    return {
        "status": "ok",
        "format": "markdown",
        "path": path,
    }
