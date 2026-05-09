#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
TARGET="${1:-all}"

build_go() {
  echo "  [go] Building gateway..."
  cd "$ROOT_DIR/backend/go-gateway"
  go mod tidy
  go build -ldflags="-s -w" -o bin/gateway ./cmd/gateway
  echo "  [go] Built: backend/go-gateway/bin/gateway"
}

build_python() {
  echo "  [python] Installing dependencies..."
  cd "$ROOT_DIR/backend/python-ai-service"
  pip install -e ".[dev]" --quiet
  echo "  [python] Dependencies installed."
}

build_rust() {
  echo "  [rust] Building broker..."
  cd "$ROOT_DIR/backend/rust-broker"
  cargo build --release
  echo "  [rust] Built: backend/rust-broker/target/release/jarvis-broker"
}

build_frontend() {
  echo "  [frontend] Building..."
  cd "$ROOT_DIR/frontend"
  npm install --silent
  npm run build
  echo "  [frontend] Built: frontend/dist/"
}

case "$TARGET" in
  go)       build_go ;;
  python)   build_python ;;
  rust)     build_rust ;;
  frontend) build_frontend ;;
  all)
    build_go
    build_python
    build_rust
    build_frontend
    ;;
  *)
    echo "Usage: $0 [go|python|rust|frontend|all]"
    exit 1
    ;;
esac

echo ""
echo "  Build complete."
