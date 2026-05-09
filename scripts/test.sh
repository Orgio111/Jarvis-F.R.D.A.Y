#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
TARGET="${1:-all}"
FAILED=0

run_go_tests() {
  echo "  [go] Running tests..."
  cd "$ROOT_DIR/backend/go-gateway"
  go test ./... -v 2>&1 || FAILED=1
}

run_python_tests() {
  echo "  [python] Running tests..."
  cd "$ROOT_DIR/backend/python-ai-service"
  python -m pytest tests/ -v 2>&1 || FAILED=1
}

run_frontend_tests() {
  echo "  [frontend] Running tests..."
  cd "$ROOT_DIR/frontend"
  npm run test -- --run 2>&1 || FAILED=1
}

case "$TARGET" in
  go)       run_go_tests ;;
  python)   run_python_tests ;;
  frontend) run_frontend_tests ;;
  all)
    run_go_tests
    run_python_tests
    run_frontend_tests
    ;;
  *)
    echo "Usage: $0 [go|python|frontend|all]"
    exit 1
    ;;
esac

if [ "$FAILED" -ne 0 ]; then
  echo ""
  echo "  TESTS FAILED"
  exit 1
else
  echo ""
  echo "  All tests passed."
fi
