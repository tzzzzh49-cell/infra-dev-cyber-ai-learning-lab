import os
import time
import uuid
from pathlib import Path
from threading import Lock

from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.responses import JSONResponse

from app.auth import client_ip, require_permissions
from app.diagnostics import (
    collect_network_diagnostic,
    write_json_report,
    write_markdown_report,
)
from app.logging_config import configure_logging

APP_VERSION = "0.3.2"
VPS_MODE = os.environ.get("APP_ENV", "").strip().lower() == "vps"

# ponytail: one global lock is enough for this lab; use a job queue only if
# concurrent diagnostics become a measured requirement.
DIAG_EXECUTION_LOCK = Lock()

logger = configure_logging(__name__)

app = FastAPI(
    title="Infra Dev Cyber AI Learning Lab API",
    description="Mini API locale pour apprendre le DevOps, Docker et les diagnostics.",
    version=APP_VERSION,
    docs_url=None if VPS_MODE else "/docs",
    redoc_url=None if VPS_MODE else "/redoc",
    openapi_url=None if VPS_MODE else "/openapi.json",
)


@app.middleware("http")
async def audit_http_request(request: Request, call_next):
    """Add a request ID, safe audit fields and uniform internal errors."""
    request_id = uuid.uuid4().hex
    request.state.request_id = request_id
    request.state.auth_identity = "anonymous"
    request.state.auth_result = "not-required"
    started_at = time.monotonic()

    try:
        response = await call_next(request)
    except Exception:
        request.state.auth_result = "error"
        logger.exception("Unhandled HTTP request error request_id=%s", request_id)
        response = JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "detail": "Internal server error.",
                "request_id": request_id,
            },
        )

    response.headers["X-Request-ID"] = request_id
    if request.url.path.startswith("/diag"):
        response.headers["Cache-Control"] = "no-store"

    logger.info(
        "HTTP request request_id=%s method=%s path=%r status=%s "
        "duration_ms=%.3f client_ip=%s identity=%s auth=%s",
        request_id,
        request.method,
        request.url.path,
        response.status_code,
        (time.monotonic() - started_at) * 1000,
        client_ip(request),
        request.state.auth_identity,
        request.state.auth_result,
    )
    return response


def collect_diagnostic_serialized():
    """Run one diagnostic at a time and reject excess concurrent work."""
    if not DIAG_EXECUTION_LOCK.acquire(blocking=False):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="A diagnostic is already running.",
            headers={"Retry-After": "1"},
        )
    try:
        return collect_network_diagnostic()
    finally:
        DIAG_EXECUTION_LOCK.release()


def command_status(section: dict) -> dict:
    """Return command health without raw command output or local identifiers."""
    return {
        "available": bool(section.get("available")),
        "ok": section.get("returncode") == 0,
        "timed_out": bool(section.get("timed_out")),
        "duration_seconds": section.get("duration_seconds", 0.0),
        "error_type": section.get("error_type") or None,
    }


def diagnostic_api_view(report: dict) -> dict:
    """Reduce a full local diagnostic to a safe HTTP status summary."""
    network = report["network"]
    resources = report["resources"]
    resolver = network["dns"]["resolver_commands"].get("selected") or {}
    return {
        "metadata": report["metadata"],
        "checks": {
            "interfaces": command_status(network["interfaces"]),
            "routes": command_status(network["routes"]),
            "dns": command_status(resolver),
            "ports": command_status(network["ports"]),
            "disk": command_status(resources["disk"]),
            "memory": command_status(resources["memory"]),
            "docker": command_status(report["docker"]),
        },
        "security": {
            "read_only": report["security"]["read_only"],
            "destructive_commands_used": report["security"][
                "destructive_commands_used"
            ],
        },
    }


diag_read_access = require_permissions("diagnostic:read")
diag_export_access = require_permissions("diagnostic:export", require_mfa=True)


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


@app.get("/diag", dependencies=[Depends(diag_read_access)])
def diag():
    """Return a minimized read-only diagnostic status."""
    return diagnostic_api_view(collect_diagnostic_serialized())


@app.post("/diag/export/json", dependencies=[Depends(diag_export_access)])
def export_diag_json():
    """Write a read-only diagnostic report as JSON."""
    report = collect_diagnostic_serialized()
    path = write_json_report(report)
    return {
        "status": "ok",
        "format": "json",
        "report_id": Path(path).stem,
    }


@app.post("/diag/export/markdown", dependencies=[Depends(diag_export_access)])
def export_diag_markdown():
    """Write a read-only diagnostic report as Markdown."""
    report = collect_diagnostic_serialized()
    path = write_markdown_report(report)
    return {
        "status": "ok",
        "format": "markdown",
        "report_id": Path(path).stem,
    }
