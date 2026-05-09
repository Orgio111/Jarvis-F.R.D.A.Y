.PHONY: help dev dev-gpu frontend-dev build build-go build-python build-rust \
        test test-go test-python test-frontend lint lint-go lint-python lint-frontend \
        docker-build docker-up docker-down docker-gpu-up gpu-check clean \
        install-go-deps install-python-deps install-frontend-deps seed-env

COMPOSE        := docker compose -f deploy/docker-compose.yml
COMPOSE_GPU    := docker compose -f deploy/docker-compose.yml -f deploy/docker-compose.gpu.yml
BACKEND_DIR    := backend
GO_DIR         := $(BACKEND_DIR)/go-gateway
PYTHON_DIR     := $(BACKEND_DIR)/python-ai-service
RUST_DIR       := $(BACKEND_DIR)/rust-broker
FRONTEND_DIR   := frontend

# ─── Help ─────────────────────────────────────────────────────────────────────
help:
	@echo ""
	@echo "  JARVIS — AI Operating System"
	@echo ""
	@echo "  make dev              Start all backend services (CPU mode, Docker)"
	@echo "  make dev-gpu          Start all backend services with GPU support"
	@echo "  make frontend-dev     Start frontend Vite dev server"
	@echo "  make build            Build all services"
	@echo "  make test             Run all tests"
	@echo "  make lint             Lint all code"
	@echo "  make gpu-check        Check if NVIDIA GPU is available via Docker"
	@echo "  make docker-up        docker compose up (CPU)"
	@echo "  make docker-down      docker compose down"
	@echo "  make docker-gpu-up    docker compose up (GPU)"
	@echo "  make seed-env         Copy .env.example files to .env (if not present)"
	@echo "  make clean            Remove build artifacts"
	@echo ""

# ─── Environment ──────────────────────────────────────────────────────────────
seed-env:
	@[ -f backend/.env ] || cp backend/.env.example backend/.env && echo "Created backend/.env"
	@[ -f frontend/.env ] || cp frontend/.env.example frontend/.env && echo "Created frontend/.env"

# ─── Dev ──────────────────────────────────────────────────────────────────────
dev: seed-env docker-up

dev-gpu: seed-env docker-gpu-up

frontend-dev:
	cd $(FRONTEND_DIR) && npm run dev

# ─── Docker ───────────────────────────────────────────────────────────────────
docker-build:
	$(COMPOSE) build

docker-up:
	$(COMPOSE) up -d
	@echo ""
	@echo "  Services started:"
	@echo "    Go Gateway  → http://localhost:8000"
	@echo "    Python AI   → http://localhost:8100 (internal)"
	@echo "    Rust Broker → http://localhost:8200 (internal)"
	@echo "    Redis       → redis://localhost:6379"
	@echo "    Prometheus  → http://localhost:9090"
	@echo "    Grafana     → http://localhost:3000"
	@echo "    Jaeger      → http://localhost:16686"
	@echo ""

docker-down:
	$(COMPOSE) down

docker-gpu-up:
	$(COMPOSE_GPU) up -d

docker-logs:
	$(COMPOSE) logs -f

docker-ps:
	$(COMPOSE) ps

# ─── GPU ──────────────────────────────────────────────────────────────────────
gpu-check:
	@echo "Checking NVIDIA GPU availability..."
	docker run --rm --gpus all nvidia/cuda:12.4.1-base-ubuntu22.04 nvidia-smi 2>/dev/null \
		&& echo "GPU available!" \
		|| echo "GPU not available or NVIDIA Container Toolkit not installed."

# ─── Build ────────────────────────────────────────────────────────────────────
build: build-go build-python build-rust build-frontend

build-go:
	cd $(GO_DIR) && go mod tidy && go build -o bin/gateway ./cmd/gateway

build-python:
	cd $(PYTHON_DIR) && pip install -e ".[dev]"

build-rust:
	cd $(RUST_DIR) && cargo build --release

build-frontend:
	cd $(FRONTEND_DIR) && npm install && npm run build

# ─── Test ─────────────────────────────────────────────────────────────────────
test: test-go test-python test-frontend

test-go:
	cd $(GO_DIR) && go test ./...

test-python:
	cd $(PYTHON_DIR) && python -m pytest tests/ -v

test-frontend:
	cd $(FRONTEND_DIR) && npm run test

# ─── Lint ─────────────────────────────────────────────────────────────────────
lint: lint-go lint-python lint-frontend

lint-go:
	cd $(GO_DIR) && go vet ./... && (which golangci-lint && golangci-lint run || true)

lint-python:
	cd $(PYTHON_DIR) && (which ruff && ruff check app/ || true)

lint-frontend:
	cd $(FRONTEND_DIR) && npm run lint

# ─── Install Deps ─────────────────────────────────────────────────────────────
install-go-deps:
	cd $(GO_DIR) && go mod tidy

install-python-deps:
	cd $(PYTHON_DIR) && pip install -e ".[dev]"

install-frontend-deps:
	cd $(FRONTEND_DIR) && npm install

install-tauri-deps:
	cd $(FRONTEND_DIR) && npm install && cargo build --manifest-path src-tauri/Cargo.toml

# ─── Clean ────────────────────────────────────────────────────────────────────
clean:
	rm -rf $(GO_DIR)/bin/
	rm -rf $(FRONTEND_DIR)/dist/
	rm -rf $(FRONTEND_DIR)/node_modules/
	find $(PYTHON_DIR) -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find $(PYTHON_DIR) -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	cd $(RUST_DIR) && cargo clean
