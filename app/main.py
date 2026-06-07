import platform
import socket
from datetime import UTC, datetime

from fastapi import FastAPI

app = FastAPI(
    title="Voice Controlled Network Lab API",
    description="Mini API locale pour apprendre le DevOps, Docker et les diagnostics.",
    version="0.1.0",
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
        "app": "voice-controlled-network-lab-api",
        "version": "0.1.0",
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
