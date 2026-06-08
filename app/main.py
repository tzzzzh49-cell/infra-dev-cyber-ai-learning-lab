from fastapi import FastAPI

from app.diagnostics import (
    collect_network_diagnostic,
    write_json_report,
    write_markdown_report,
)

APP_VERSION = "0.3.0"

app = FastAPI(
    title="Infra Dev Cyber AI Learning Lab API",
    description="Mini API locale pour apprendre le DevOps, Docker et les diagnostics.",
    version=APP_VERSION,
)


@app.get("/")
def root():
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
def health():
    return {
        "status": "ok",
        "service": "lab-api",
    }


@app.get("/version")
def version():
    return {
        "app": "infra-dev-cyber-ai-learning-lab-api",
        "version": APP_VERSION,
    }


@app.get("/diag")
def diag():
    return collect_network_diagnostic()


@app.post("/diag/export/json")
def export_diag_json():
    report = collect_network_diagnostic()
    path = write_json_report(report)
    return {
        "status": "ok",
        "format": "json",
        "path": path,
    }


@app.post("/diag/export/markdown")
def export_diag_markdown():
    report = collect_network_diagnostic()
    path = write_markdown_report(report)
    return {
        "status": "ok",
        "format": "markdown",
        "path": path,
    }
