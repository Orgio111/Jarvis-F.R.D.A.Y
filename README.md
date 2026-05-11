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

GPU is **optional**. The system runs fully in CPU mode.

Set `GPU_REQUIRED=false` (default) to allow CPU fallback.
Set `GPU_REQUIRED=true` only if GPU is mandatory.

GPU-accelerated workloads (when available):
- Local LLM inference
- STT (Whisper/faster-whisper)
- Sentence-Transformers embeddings
- FAISS vector search
- Vision model inference

## License


MIT
