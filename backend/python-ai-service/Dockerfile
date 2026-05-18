FROM python:3.11-slim AS base

WORKDIR /app

# System dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential curl git \
    && rm -rf /var/lib/apt/lists/*

# Copy project metadata first for layer caching
COPY pyproject.toml ./

# Hard-require numpy because app imports it at module import time.
RUN pip install --no-cache-dir "numpy>=1.26.0"

# Install base dependencies (no GPU extras by default)
# Use non-editable install to avoid PEP660 build_editable hook issues.
RUN pip install --no-cache-dir "."

# Copy source
COPY app/ ./app/

ENV APP_HOST=0.0.0.0
ENV APP_PORT=8100
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

EXPOSE 8100

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8100", "--workers", "1"]

# ─── GPU variant (nvidia/cuda base) ────────────────────────────────────────────
FROM nvidia/cuda:12.4.1-runtime-ubuntu22.04 AS gpu

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3.11 python3-pip python3.11-dev build-essential curl git \
    && rm -rf /var/lib/apt/lists/*

RUN ln -sf /usr/bin/python3.11 /usr/bin/python3 && ln -sf /usr/bin/python3 /usr/bin/python

WORKDIR /app
COPY pyproject.toml ./

# Upgrade pip and setuptools
RUN pip install --no-cache-dir --upgrade pip "setuptools>=70" wheel

# Hard-require numpy because app imports it at module import time (fail-fast otherwise)
RUN pip install --no-cache-dir "numpy>=1.26.0"

# Install base dependencies first, then GPU extras separately to ensure all deps are included
RUN pip install --no-cache-dir "." && \
    pip install --no-cache-dir ".[gpu-cuda]"

COPY app/ ./app/

ENV APP_HOST=0.0.0.0
ENV APP_PORT=8100
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Add pip binary directory to PATH
ENV PATH="/usr/local/bin:$PATH"

EXPOSE 8100

# Use python -m uvicorn to avoid any PATH issues
CMD ["python3", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8100", "--workers", "1"]
