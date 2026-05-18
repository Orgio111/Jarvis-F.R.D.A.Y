# JARVIS — Autonomous AI Operating System

A production-ready, full-stack, JARVIS-inspired Autonomous AI Operating System.

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│  Frontend (React/Vite/Tauri)   http://localhost:5173                │
│  JARVIS Cockpit UI                                                   │
└────────────────────────┬────────────────────────────────────────────┘
                         │ REST / WebSocket / SSE
                         ▼
┌─────────────────────────────────────────────────────────────────────┐
│  Go API Gateway                http://localhost:8000                │
│  Public REST + WebSocket + SSE layer                                │
└──────────┬──────────────────────────────────────┬──────────────────┘
           │ HTTP (internal)                      │ HTTP (internal)
           ▼                                      ▼
┌──────────────────────────┐          ┌───────────────────────┐
│  Python FastAPI          │          │  Rust Tokio Broker    │
│  AI Service :8100        │◄────────►│  Event Bus :8200      │
│  GPU / LLM / Voice /     │          │  Redis Pub/Sub relay  │
│  Memory / Search / Tools │          └──────────┬────────────┘
└──────────┬───────────────┘                     │
           │                                     ▼
           ▼                          ┌───────────────────────┐
┌──────────────────────────┐          │  Redis :6379          │
│  NVIDIA NIM / OpenRouter │          │  Cache / Sessions /   │
│  Local LLM / STT / TTS   │          │  Pub/Sub              │
│  FAISS / Embeddings      │          └───────────────────────┘
└──────────────────────────┘
```

## Quick Start

### Prerequisites

- Docker + Docker Compose v2
- Go 1.22+
- Python 3.11+
- Node.js 20+
- Rust 1.78+ (for Tauri desktop build)

### 1 — Clone and configure

```bash
git clone <repo>
cd Jarvis-F.R.D.A.Y

# Backend environment
cp backend/.env.example backend/.env
# Edit backend/.env — add NVIDIA_NIM_API_KEY and/or OPENROUTER_API_KEY

# Frontend environment
cp frontend/.env.example frontend/.env
```

### 2 — Start with Docker Compose (recommended)

```bash
mingw32-make dev
```

This starts all backend services. Then in a separate terminal:

```bash
mingw32-make frontend-dev
```

Open http://localhost:5173

### 3 — GPU support (optional)

Check if GPU is available:

```bash
mingw32-make gpu-check
```

Start with GPU acceleration:

```bash
mingw32-make dev-gpu
```

## Services

| Service | URL | Description |
|---|---|---|
| Frontend | http://localhost:5173 | JARVIS cockpit UI |
| Go Gateway | http://localhost:8000 | Public REST/WS/SSE API |
| Python AI | http://localhost:8100 | Internal AI service |
| Rust Broker | http://localhost:8200 | Internal event bus |
| Redis | redis://localhost:6379 | Cache / pub-sub |
| Prometheus | http://localhost:9090 | Metrics |
| Grafana | http://localhost:3000 | Dashboards |
| Jaeger | http://localhost:16686 | Distributed tracing |

## Key API Endpoints

```
GET  /api/health
GET  /api/bootstrap
GET  /api/system/status
GET  /api/gpu/status
GET  /api/providers
POST /api/chat/send
GET  /api/chat/stream/{requestId}   (SSE)
WS   /ws/chat
POST /api/voice/transcribe
POST /api/voice/synthesize
WS   /ws/voice/{sessionId}
```

All REST responses use the canonical envelope:

```json
{ "ok": true, "data": {}, "correlationId": "...", "timestamp": "..." }
{ "ok": false, "error": { "code": "...", "message": "..." }, "correlationId": "...", "timestamp": "..." }
```

## Development

```bash
make help          # Show all targets
make dev           # Start all backend services (CPU mode)
make dev-gpu       # Start with GPU support
make frontend-dev  # Start frontend dev server
make test          # Run all tests
make lint          # Lint all code
make build         # Build all binaries
make clean         # Remove build artifacts
```

## Security

- Provider API keys are stored only in backend `.env`
- Frontend communicates only with `http://localhost:8000`
- No secrets are ever sent to the frontend
- Sandbox execution is network-isolated by default
- Local admin actions require explicit approval

## GPU Acceleration

GPU is **optional**. The system runs fully in CPU mode when no GPU is present.

### Prerequisites (NVIDIA)

1. Install **NVIDIA Container Toolkit** on the host:
   ```bash
   # Ubuntu / Debian
   curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
   curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list | \
     sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
     sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list
   sudo apt-get update && sudo apt-get install -y nvidia-container-toolkit
   sudo nvidia-ctk runtime configure --runtime=docker
   sudo systemctl restart docker
   ```

2. Verify the GPU is visible to Docker:
   ```bash
   docker run --rm --gpus all nvidia/cuda:12.4.1-base-ubuntu22.04 nvidia-smi
   ```
   You should see your GPU listed (e.g. **NVIDIA GeForce RTX 4050 Laptop GPU**).

### Running with GPU

```bash
# GPU-accelerated stack (RTX 4050 / any CUDA 12.x GPU)
docker compose -f docker-compose.yml -f docker-compose.gpu.yml up --build

# CPU-only (no changes needed)
docker compose up --build
```

### GPU support matrix

| GPU | Architecture | CUDA | Supported |
|-----|-------------|------|-----------|
| RTX 4050 Laptop | Ada Lovelace (sm_89) | 12.x | ✅ |
| RTX 3000 series | Ampere (sm_86) | 11.x+ | ✅ |
| RTX 2000 series | Turing (sm_75) | 10.x+ | ✅ |
| GTX 1000 series | Pascal (sm_61) | 10.x+ | ✅ |

### GPU-accelerated workloads

| Workload | GPU concurrency | Notes |
|----------|----------------|-------|
| STT — faster-whisper | 2 | `float16` on CUDA, `int8` on CPU |
| Embeddings — sentence-transformers | 4 | |
| Vision | 2 | |
| Local LLM | 1 | sequential per instance |
| TTS | 2 | CPU pyttsx3 fallback if no GPU engine |
| FAISS | 8 | CPU index (fast enough, avoids faiss-gpu complexity) |

Set `GPU_REQUIRED=false` (default) to allow CPU fallback.
Set `GPU_REQUIRED=true` only if you want the service to refuse to start without a GPU.

## License


MIT
