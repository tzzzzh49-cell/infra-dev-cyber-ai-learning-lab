import platform
import socket
from datetime import UTC, datetime

from fastapi import FastAPI

app = FastAPI(
    title="Infra Dev Cyber AI Learning Lab API",
    description="Mini API locale pour apprendre le DevOps, Docker et les diagnostics.",
    version="0.2.0",
)


@app.get("/")
def root():
    return {
        "message": "Mini API locale active",
        "endpoints": ["/health", "/version", "/diag"],
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
        "version": "0.2.0",
    }


@app.get("/diag")
def diag():
    return {
        "hostname": socket.gethostname(),
        "platform": platform.system(),
        "platform_version": platform.version(),
        "python_version": platform.python_version(),
        "time_utc": datetime.now(UTC).isoformat(),
    }
