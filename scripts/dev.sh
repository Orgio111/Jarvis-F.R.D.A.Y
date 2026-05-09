#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"

GPU_MODE="${1:-cpu}"

echo ""
echo "  ╔══════════════════════════════════════════╗"
echo "  ║   JARVIS — AI Operating System           ║"
echo "  ╚══════════════════════════════════════════╝"
echo ""

# Ensure env files exist
if [ ! -f "$ROOT_DIR/backend/.env" ]; then
  echo "  [setup] Creating backend/.env from example..."
  cp "$ROOT_DIR/backend/.env.example" "$ROOT_DIR/backend/.env"
fi

if [ ! -f "$ROOT_DIR/frontend/.env" ]; then
  echo "  [setup] Creating frontend/.env from example..."
  cp "$ROOT_DIR/frontend/.env.example" "$ROOT_DIR/frontend/.env"
fi

# Start Docker Compose
if [ "$GPU_MODE" = "gpu" ]; then
  echo "  [docker] Starting services with GPU support..."
  docker compose -f "$ROOT_DIR/deploy/docker-compose.yml" \
                 -f "$ROOT_DIR/deploy/docker-compose.gpu.yml" \
                 up -d
else
  echo "  [docker] Starting services in CPU mode..."
  docker compose -f "$ROOT_DIR/deploy/docker-compose.yml" up -d
fi

echo ""
echo "  Services:"
echo "    Go Gateway  → http://localhost:8000/api/health"
echo "    Prometheus  → http://localhost:9090"
echo "    Grafana     → http://localhost:3000"
echo "    Jaeger      → http://localhost:16686"
echo ""
echo "  Start frontend: cd frontend && npm run dev"
echo "  UI at: http://localhost:5173"
echo ""
