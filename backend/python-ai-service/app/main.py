from __future__ import annotations

import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.core.errors import JarvisError, jarvis_error_handler, generic_error_handler
from app.core.logging import get_logger, setup_logging
from app.db.database import init_db, _session_factory
from app.gpu.detector import GPUDetector
from app.gpu.workload_router import WorkloadRouter
from app.providers.router import ProviderRouter
from app.routers import (
    health, bootstrap, gpu, system, providers, models, chat,
    voice, memory, execution, tools, search, vision, self_improvement,
    local_actions,
)
from app.routers import skills, profile, agent, scheduler as scheduler_router
from app.routers.gpu import set_workload_router

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    setup_logging(settings.app_env)

    logger.info("starting_jarvis_ai_service", version="0.2.0", env=settings.app_env)

    # ── Database ──────────────────────────────────────────────────────────────
    await init_db()
    logger.info("database_ready")

    # ── GPU detection ─────────────────────────────────────────────────────────
    await GPUDetector.initialize()
    gpu_info = GPUDetector.get_info()
    logger.info(
        "gpu_init_complete",
        cuda_available=gpu_info.cuda_available,
        device_count=gpu_info.device_count,
    )
    if settings.gpu_required and not gpu_info.cuda_available:
        raise RuntimeError(
            "GPU_REQUIRED=true but no CUDA device is available. "
            "Set GPU_REQUIRED=false to allow CPU fallback."
        )

    # ── Workload router ───────────────────────────────────────────────────────
    workload_router = WorkloadRouter(settings)
    set_workload_router(workload_router)

    # ── Provider initialisation ───────────────────────────────────────────────
    try:
        ProviderRouter.initialize(settings)
        logger.info("provider_router_initialized")
    except Exception as exc:
        logger.warning("provider_router_init_warning", error=str(exc))

    # ── Memory service warm-up (loads embedder + FAISS index) ─────────────────
    if settings.faiss_enabled:
        try:
            from app.db.database import _session_factory as sf
            from app.services import memory_service
            async with sf() as db:
                await memory_service.boot(db, settings.embeddings_model)
            logger.info("memory_service_ready")
        except Exception as exc:
            logger.warning("memory_boot_warning", error=str(exc))

    # ── Scheduler ─────────────────────────────────────────────────────────────
    try:
        from app.scheduler.worker import SchedulerWorker
        worker = SchedulerWorker.initialize(_session_factory)
        await worker.start()
        logger.info("scheduler_ready")
    except Exception as exc:
        logger.warning("scheduler_init_warning", error=str(exc))

    logger.info("jarvis_ai_service_ready", host=settings.app_host, port=settings.app_port)

    yield

    # ── Shutdown ──────────────────────────────────────────────────────────────
    logger.info("jarvis_ai_service_shutting_down")
    try:
        from app.scheduler.worker import SchedulerWorker
        await SchedulerWorker.get().stop()
    except Exception:
        pass


settings = get_settings()

app = FastAPI(
    title="JARVIS Python AI Service",
    description="Internal AI microservice — GPU, providers, voice, memory, skills, agent, scheduler",
    version="0.2.0",
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


# ─── Prometheus metrics ───────────────────────────────────────────────────────
if settings.prometheus_enabled:
    try:
        from prometheus_fastapi_instrumentator import Instrumentator
        Instrumentator().instrument(app).expose(app, endpoint="/metrics")
    except ImportError:
        pass

# ─── OpenTelemetry tracing ────────────────────────────────────────────────────
if settings.otel_enabled:
    try:
        from app.core.tracing import init_tracing
        init_tracing(
            app,
            service_name=settings.otel_service_name,
            environment=settings.app_env,
            jaeger_endpoint=settings.jaeger_endpoint,
            sample_rate=getattr(settings, "otel_sample_rate", 1.0),
        )
    except Exception as exc:
        logger.warning("otel_init_warning", error=str(exc))

# ─── Routers ──────────────────────────────────────────────────────────────────
# Core
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
app.include_router(search.router)
app.include_router(vision.router)
app.include_router(self_improvement.router)
app.include_router(local_actions.router)

# New — persistent memory, skills, profile, agent loop, scheduler
app.include_router(skills.router)
app.include_router(profile.router)
app.include_router(agent.router)
app.include_router(scheduler_router.router)
