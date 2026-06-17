import hashlib
import os
from secrets import compare_digest
from typing import Annotated

from fastapi import Depends, FastAPI, Header, HTTPException, status

from app.diagnostics import (
    collect_network_diagnostic,
    write_json_report,
    write_markdown_report,
)

APP_VERSION = "0.3.2"
DIAG_TOKEN_ENV = "DIAG_ACCESS_TOKEN"
DIAG_TOKEN_HASH_ENV = "DIAG_ACCESS_TOKEN_SHA256"
PROTECTED_APP_ENVS = {"vps", "production", "prod"}

app = FastAPI(
    title="Infra Dev Cyber AI Learning Lab API",
    description="Mini API locale pour apprendre le DevOps, Docker et les diagnostics.",
    version=APP_VERSION,
)


def diag_protection_enabled() -> bool:
    app_env = os.environ.get("APP_ENV", "").strip().lower()
    return (
        app_env in PROTECTED_APP_ENVS
        or bool(os.environ.get(DIAG_TOKEN_ENV))
        or bool(os.environ.get(DIAG_TOKEN_HASH_ENV))
    )


def hash_diag_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def configured_diag_token_hash() -> str | None:
    configured_hash = os.environ.get(DIAG_TOKEN_HASH_ENV, "").strip().lower()
    if configured_hash:
        return configured_hash

    configured_token = os.environ.get(DIAG_TOKEN_ENV, "")
    if configured_token:
        return hash_diag_token(configured_token)
    return None


async def require_diag_access(
    authorization: Annotated[str | None, Header()] = None,
    x_diag_token: Annotated[str | None, Header(alias="X-Diag-Token")] = None,
) -> None:
    if not diag_protection_enabled():
        return

    expected_token_hash = configured_diag_token_hash()
    if not expected_token_hash:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Diagnostic access token hash is required in this environment.",
        )

    provided_token = x_diag_token
    if authorization:
        scheme, _, token = authorization.partition(" ")
        if scheme.lower() == "bearer" and token:
            provided_token = token

    provided_token_hash = hash_diag_token(provided_token) if provided_token else ""
    if not provided_token or not compare_digest(
        provided_token_hash,
        expected_token_hash,
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Diagnostic authentication required.",
            headers={"WWW-Authenticate": "Bearer"},
        )


@app.get("/")
async def root():
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


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "service": "lab-api",
    }


@app.get("/version")
async def version():
    return {
        "app": "infra-dev-cyber-ai-learning-lab-api",
        "version": APP_VERSION,
    }


@app.get("/diag", dependencies=[Depends(require_diag_access)])
async def diag():
    return collect_network_diagnostic()


@app.post("/diag/export/json", dependencies=[Depends(require_diag_access)])
async def export_diag_json():
    report = collect_network_diagnostic()
    path = write_json_report(report)
    return {
        "status": "ok",
        "format": "json",
        "path": path,
    }


@app.post("/diag/export/markdown", dependencies=[Depends(require_diag_access)])
async def export_diag_markdown():
    report = collect_network_diagnostic()
    path = write_markdown_report(report)
    return {
        "status": "ok",
        "format": "markdown",
        "path": path,
    }
