# syntax=docker/dockerfile:1
#
# Multi-stage build:
#   base    - slim Python + production dependencies + application code
#   test    - base + dev dependencies + tests  (docker build --target test)
#   runtime - base, run as non-root with gunicorn (default target)

ARG PYTHON_VERSION=3.12

# ---------- base ----------
FROM python:${PYTHON_VERSION}-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    ACEEST_DB=/app/data/aceest_fitness.db

WORKDIR /app

# Unprivileged user; only the data directory is writable by it.
RUN groupadd --system app \
    && useradd --system --gid app --no-create-home --shell /usr/sbin/nologin app \
    && mkdir -p /app/data \
    && chown app:app /app/data

# Dependencies first so this layer is cached until requirements change.
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY app.py .
COPY aceest/ aceest/

# ---------- test ----------
FROM base AS test

COPY requirements-dev.txt pytest.ini ./
RUN pip install -r requirements-dev.txt
COPY tests/ tests/

ENV COVERAGE_FILE=/tmp/.coverage
USER app
CMD ["pytest", "-v", "-p", "no:cacheprovider"]

# ---------- runtime ----------
FROM base AS runtime

USER app
EXPOSE 5000

HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:5000/health', timeout=2)" || exit 1

# --preload initialises the database once in the master before forking workers.
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "--preload", "--access-logfile", "-", "app:app"]
