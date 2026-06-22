# syntax=docker/dockerfile:1.7

FROM python:3.12.13-slim-bookworm AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /build

# The Compose build context is the repository root. Copy only the pinned runtime
# requirements first so dependency layers stay cacheable and auditable.
COPY app/requirements.txt ./app/requirements.txt

RUN python -m venv /opt/venv \
    && /opt/venv/bin/pip install --no-cache-dir --requirement app/requirements.txt

FROM python:3.12.13-slim-bookworm AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:${PATH}" \
    DIAG_COMMAND_TIMEOUT=3

WORKDIR /workspace

# Keep the runtime user non-root. UID/GID 10001 are explicit so Compose can
# enforce the same identity and mounted report files are not written as root.
RUN groupadd --gid 10001 appuser \
    && useradd --uid 10001 --gid appuser --home-dir /workspace --shell /usr/sbin/nologin --no-create-home appuser \
    && mkdir -p /workspace/outputs/logs /workspace/outputs/reports \
    && mkdir -p /workspace/config \
    && chown -R appuser:appuser /workspace/outputs

COPY --from=builder /opt/venv /opt/venv

# Runtime application code stays root-owned and read-only to the runtime user.
# The .dockerignore excludes tests, dev requirements and generated outputs.
COPY app ./app

# Operational examples are kept outside the importable app package. This avoids
# copying the full repository into /workspace/app while preserving useful
# Compose, Caddy and script references for inspection in the image.
COPY compose.yaml ./config/compose.yaml
COPY docs/vps/Caddyfile.example ./config/Caddyfile.example
COPY scripts ./config/scripts

USER 10001:10001

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
