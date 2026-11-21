# JTech Tally Bridge - Production image
# Multi-stage build: install deps in builder, copy into slim final image.

FROM python:3.12-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /build

# System deps for building Python wheels
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libxml2-dev libxslt1-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN python -m venv /opt/venv \
    && /opt/venv/bin/pip install --upgrade pip \
    && /opt/venv/bin/pip install -r requirements.txt


# ---- Final image ----
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH" \
    DJANGO_SETTINGS_MODULE=web.settings

# Runtime deps: libxml2 for openpyxl/lxml, curl for healthcheck
RUN apt-get update && apt-get install -y --no-install-recommends \
    libxml2 libxslt1.1 curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN groupadd --system jtech && useradd --system --gid jtech jtech

WORKDIR /app

# Copy venv from builder
COPY --from=builder /opt/venv /opt/venv

# Copy application code
COPY --chown=jtech:jtech . /app/

# Create writable data dir
RUN mkdir -p /app/data && chown -R jtech:jtech /app/data
VOLUME ["/app/data"]

USER jtech

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=20s --retries=3 \
    CMD curl -fsS http://localhost:8000/health/ || exit 1

# Default: gunicorn. Override via docker-compose for scheduler.
CMD ["gunicorn", "--bind", "0.0.0.0:8000", \
     "--workers", "3", \
     "--threads", "2", \
     "--access-logfile", "-", \
     "--error-logfile", "-", \
     "web.wsgi:application"]
