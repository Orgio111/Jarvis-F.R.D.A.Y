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

# ─── GPU variant (NVIDIA CUDA 12.4 base — covers RTX 4050 Ada Lovelace) ───────
# nvidia/cuda:12.4.1-cudnn-runtime ships cuDNN which is required by PyTorch,
# faster-whisper, and onnxruntime-gpu.
FROM nvidia/cuda:12.4.1-cudnn-runtime-ubuntu22.04 AS gpu

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3.11 python3-pip python3.11-dev build-essential curl git \
    && rm -rf /var/lib/apt/lists/*

RUN ln -sf /usr/bin/python3.11 /usr/bin/python3 && ln -sf /usr/bin/python3 /usr/bin/python

WORKDIR /app
COPY pyproject.toml ./

# Upgrade pip / build tools
RUN pip install --no-cache-dir --upgrade pip "setuptools>=70" wheel

# ── Step 1: install PyTorch with CUDA 12.1 wheels from the official index ─────
# CUDA 12.1 wheels run on any CUDA 12.x driver (12.4 included).
# RTX 4050 Laptop (Ada Lovelace, sm_89) is fully supported from PyTorch 2.1+.
RUN pip install --no-cache-dir \
    torch>=2.3.0 \
    --index-url https://download.pytorch.org/whl/cu121

# ── Step 2: numpy (must precede pip install . ) ────────────────────────────────
RUN pip install --no-cache-dir "numpy>=1.26.0"

# ── Step 3: base service deps (no torch pulled here — already installed) ───────
RUN pip install --no-cache-dir "."

# ── Step 4: GPU extras (sentence-transformers, faiss-cpu, faster-whisper, onnx) 
# torch is already present so pip won't re-download it.
RUN pip install --no-cache-dir \
    "sentence-transformers>=3.0.0" \
    "faiss-cpu>=1.8.0" \
    "faster-whisper>=1.0.3" \
    "onnxruntime-gpu>=1.18.0"

COPY app/ ./app/

ENV APP_HOST=0.0.0.0
ENV APP_PORT=8100
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
# GPU detection env hints
ENV GPU_ENABLED=true
ENV GPU_ALLOW_CPU_FALLBACK=true
ENV STT_GPU_ENABLED=true
ENV EMBEDDINGS_GPU_ENABLED=true
ENV VISION_GPU_ENABLED=true
ENV TTS_GPU_ENABLED=auto

ENV PATH="/usr/local/bin:$PATH"

EXPOSE 8100

CMD ["python3", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8100", "--workers", "1"]
