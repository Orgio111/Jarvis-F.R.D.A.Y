from __future__ import annotations

import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import get_settings
from app.core.errors import JarvisError, jarvis_error_handler, generic_error_handler
from app.core.logging import get_logger, setup_logging
from app.gpu.detector import GPUDetector
from app.gpu.workload_router import WorkloadRouter
from app.providers.router import ProviderRouter
from app.routers import health, bootstrap, gpu, system, providers, models, chat, voice, memory, execution, tools
from app.routers.gpu import set_workload_router

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    setup_logging(settings.app_env)

    logger.info("starting_jarvis_ai_service", version="0.1.0", env=settings.app_env)

    # GPU detection — never fails startup
    await GPUDetector.initialize()
    gpu_info = GPUDetector.get_info()
    logger.info(
        "gpu_init_complete",
        cuda_available=gpu_info.cuda_available,
        device_count=gpu_info.device_count,
    )

    # GPU required check
    if settings.gpu_required and not gpu_info.cuda_available:
        raise RuntimeError(
            "GPU_REQUIRED=true but no CUDA device is available. "
            "Set GPU_REQUIRED=false to allow CPU fallback."
        )

    # Workload router
    workload_router = WorkloadRouter(settings)
    set_workload_router(workload_router)

    # Provider initialisation — never fails startup
    try:
        ProviderRouter.initialize(settings)
        logger.info("provider_router_initialized")
    except Exception as exc:
        logger.warning("provider_router_init_warning", error=str(exc))

    logger.info("jarvis_ai_service_ready", host=settings.app_host, port=settings.app_port)

    yield

    logger.info("jarvis_ai_service_shutting_down")


settings = get_settings()

app = FastAPI(
    title="JARVIS Python AI Service",
    description="Internal AI microservice — GPU, providers, voice, memory, search",
    version="0.1.0",
    docs_url="/docs",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

# ─── CORS (internal service — restrict to gateway only) ───────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8000", "http://go-gateway:8000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Error handlers ───────────────────────────────────────────────────────────
app.add_exception_handler(JarvisError, jarvis_error_handler)
app.add_exception_handler(Exception, generic_error_handler)

# ─── Request timing middleware ────────────────────────────────────────────────
@app.middleware("http")
async def add_timing(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    duration_ms = (time.perf_counter() - start) * 1000
    response.headers["X-Response-Time-Ms"] = f"{duration_ms:.1f}"
    return response


# ─── Prometheus metrics (optional) ───────────────────────────────────────────
if settings.prometheus_enabled:
    try:
        from prometheus_fastapi_instrumentator import Instrumentator
        Instrumentator().instrument(app).expose(app, endpoint="/metrics")
    except ImportError:
        pass

# ─── Routers ──────────────────────────────────────────────────────────────────
app.include_router(health.router)
app.include_router(bootstrap.router)
app.include_router(gpu.router)
app.include_router(system.router)
app.include_router(providers.router)
app.include_router(models.router)
app.include_router(chat.router)
app.include_router(voice.router)
app.include_router(memory.router)
app.include_router(execution.router)
app.include_router(tools.router)
