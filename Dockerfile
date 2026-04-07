# syntax=docker/dockerfile:1
# Production-oriented image: reproducible base, non-root runtime, minimal attack surface.

ARG PYTHON_VERSION=3.12
ARG PYTHON_IMAGE=python:${PYTHON_VERSION}-slim-trixie

# -----------------------------------------------------------------------------
# Builder: resolve and install dependencies into an isolated virtualenv (no dev).
# -----------------------------------------------------------------------------
FROM ${PYTHON_IMAGE} AS builder

ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=0

RUN pip install --no-cache-dir --upgrade pip setuptools wheel \
    && pip install --no-cache-dir uv

WORKDIR /build

COPY pyproject.toml uv.lock ./

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project --no-dev

COPY src ./src

# -----------------------------------------------------------------------------
# Runtime: only Python + venv + app code; no compilers, pip, or uv.
# -----------------------------------------------------------------------------
FROM ${PYTHON_IMAGE} AS runtime

ARG UID=10001
ARG GID=10001

LABEL org.opencontainers.image.title="Cartesi Knowledge MCP Server" \
      org.opencontainers.image.description="Streamable HTTP MCP server for curated Cartesi knowledge (read-only PostgreSQL)."

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONFAULTHANDLER=1 \
    PATH="/app/.venv/bin:${PATH}" \
    APP_HOST=0.0.0.0 \
    APP_PORT=8000

WORKDIR /app

RUN groupadd --gid "${GID}" app \
    && useradd \
        --uid "${UID}" \
        --gid "${GID}" \
        --shell /usr/sbin/nologin \
        --create-home \
        --home-dir /home/app \
        app

COPY --from=builder --chown=app:app /build/.venv /app/.venv
COPY --from=builder --chown=app:app /build/src /app/src

USER app

EXPOSE 8000

STOPSIGNAL SIGTERM

# Uses APP_HOST / APP_PORT from environment (see src/core/config.py).
# Start period allows async DB pool init on first traffic.
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import os, urllib.request; p=os.environ.get('APP_PORT','8000'); urllib.request.urlopen(f'http://127.0.0.1:{p}/healthz', timeout=4).read()"

CMD ["python", "-m", "src.main"]
