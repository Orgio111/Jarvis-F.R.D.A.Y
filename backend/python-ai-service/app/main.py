from __future__ import annotations

import asyncio
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
    voice, memory, execution, tools, search, vision,
)
from app.routers import skills, profile, agent, scheduler as scheduler_router
from app.routers.brain_router import router as brain_router
from app.routers.evolution_router import router as evolution_router
from app.routers.gpu import set_workload_router
from app.code_indexing.router import router as code_indexing_router
from app.workflows.router import router as workflows_router
from app.device_agent.router import router as device_agent_router
from app.reasoning.router import router as reasoning_router
from app.provider_discovery.router import router as provider_discovery_router
from app.image_generation.router import router as image_generation_router
from app.prompt_mutation.router import router as prompt_mutation_router
from app.routers.orchestrate import router as orchestrate_router

# System integrations
from app.routers import external_apis as external_apis_router
from app.routers import workflows_engine as workflows_engine_router
from app.routers import swarm_manager as swarm_manager_router
from app.routers import self_evolution as self_evolution_router
from app.routers import stt as stt_router

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

        # Sync discovered providers (non-blocking background task)
        if settings.provider_discovery_enabled:
            async def _sync_discovered():
                try:
                    pr = ProviderRouter.get()
                    count = await pr.sync_discovered()
                    logger.info("discovered_providers_synced_at_startup", count=count)
                except Exception as exc:
                    logger.warning("discovery_sync_warning", error=str(exc))

            asyncio.ensure_future(_sync_discovered())
    except Exception as exc:
        logger.warning("provider_router_init_warning", error=str(exc))

    # ── Brain architecture initialisation ──────────────────────────────────────
    try:
        from app.brain.smart_router import SmartRouter
        from app.brain.agent_reputation import AgentReputation
        from app.brain.strategy_brain import StrategyBrain
        from app.brain.macro_brain import MacroBrain
        SmartRouter.initialize()
        AgentReputation.initialize()
        StrategyBrain.initialize()
        MacroBrain.initialize()
        logger.info("brain_architecture_initialized",
                     sectors=len(__import__('app.brain.sector_brains', fromlist=['SECTOR_BRAIN_REGISTRY']).SECTOR_BRAIN_REGISTRY))
    except Exception as exc:
        logger.warning("brain_init_warning", error=str(exc))

    # ── Evolution & self-improvement services ──────────────────────────────────
    try:
        from app.services.evolution_service import EvolutionService
        from app.services.self_improvement_loop import SelfImprovementLoop
        from app.services.autonomous_pipeline import AutonomousPipeline
        from app.services.api_registry_service import ApiRegistryService
        from app.services.workflow_service import WorkflowService
        EvolutionService.initialize()
        SelfImprovementLoop.initialize()
        AutonomousPipeline.initialize()
        logger.info("evolution_services_initialized")
    except Exception as exc:
        logger.warning("evolution_init_warning", error=str(exc))

    # ── Memory service warm-up (loads embedder + FAISS index) ─────────────────
    if settings.faiss_enabled:
        try:
            from app.services import memory_service
            async with _session_factory() as db:
                await memory_service.boot(db, settings.embeddings_model)
            logger.info("memory_service_ready")
        except Exception as exc:
            logger.warning("memory_boot_warning", error=str(exc))

    # ── Semantic cache (Redis exact + Qdrant semantic) ────────────────────────
    try:
        from app.cache.semantic_cache import SemanticCache
        import os as _os
        _qdrant_host = _os.getenv("QDRANT_HOST", "qdrant")
        _qdrant_port = int(_os.getenv("QDRANT_PORT", "6333"))
        sc = SemanticCache.initialize(
            redis_url=settings.redis_url,
            qdrant_host=_qdrant_host,
            qdrant_port=_qdrant_port,
            threshold=settings.semantic_cache_threshold,
            ttl_seconds=settings.semantic_cache_ttl_seconds,
            enabled=settings.semantic_cache_enabled,
        )
        await sc.boot()
        logger.info("semantic_cache_ready")
    except Exception as exc:
        logger.warning("semantic_cache_init_warning", error=str(exc))

    # ── Scheduler ─────────────────────────────────────────────────────────────
    try:
        from app.scheduler.worker import SchedulerWorker
        worker = SchedulerWorker.initialize(_session_factory)
        await worker.start()
        logger.info("scheduler_ready")
    except Exception as exc:
        logger.warning("scheduler_init_warning", error=str(exc))

    # ── External API Registry ────────────────────────────────────────────
    try:
        ApiRegistryService.initialize(settings)
        logger.info("api_registry_service_initialized")
    except Exception as exc:
        logger.warning("api_registry_init_warning", error=str(exc))

    # ── Workflow Engine (Ruflo) ────────────────────────────────────────────
    try:
        WorkflowService.initialize(settings)
        logger.info("workflow_service_initialized")
    except Exception as exc:
        logger.warning("workflow_init_warning", error=str(exc))

    # ── Multi-Agent Communication System ──────────────────────────────────────
    try:
        from app.multi_agent.agent_bus import AgentBus
        from app.multi_agent.agent_factory import AgentFactory, AgentRegistry
        from app.multi_agent.blackboard import BlackboardRegistry
        AgentBus.get()          # initialize singleton
        AgentFactory.get()      # initialize singleton
        AgentRegistry.get()     # initialize singleton
        BlackboardRegistry.get()
        logger.info("multi_agent_system_initialized")
    except Exception as exc:
        logger.warning("multi_agent_init_warning", error=str(exc))

    # ── Swarm Manager (v3 Distributed Autonomous Swarm Intelligence) ──
    try:
        from app.services.swarm_manager_service import SwarmManagerService
        SwarmManagerService.initialize(settings)
        logger.info("swarm_manager_initialized")
    except Exception as exc:
        logger.warning("swarm_manager_init_warning", error=str(exc))

    # ── Memory Fabric (v3 Multi-Layered Cognitive Memory) ──
    try:
        from app.services.memory_fabric_service import MemoryFabricService
        MemoryFabricService.initialize(settings)
        logger.info("memory_fabric_initialized")
    except Exception as exc:
        logger.warning("memory_fabric_init_warning", error=str(exc))

    # ── Self-Evolution Engine (v3 Self-Improvement) ──
    try:
        from app.services.self_evolution_service import SelfEvolutionService
        SelfEvolutionService.initialize(settings)
        logger.info("self_evolution_initialized")
    except Exception as exc:
        logger.warning("self_evolution_init_warning", error=str(exc))

    # ── STT Service (faster-whisper GPU) ──
    if settings.stt_enabled:
        try:
            from app.services.stt_service import STTService
            STTService.initialize(settings)
            logger.info("stt_service_initialized")
        except Exception as exc:
            logger.warning("stt_service_init_warning", error=str(exc))

    # ── Skill Evolution background loop ────────────────────────────────────────
    try:
        async def _evolution_loop() -> None:
            """Run skill evolution cycle every 10 minutes."""
            from app.services.skill_evolution import run_evolution_cycle
            while True:
                await asyncio.sleep(600)  # 10 min
                try:
                    async with _session_factory() as _ev_db:
                        await run_evolution_cycle(_ev_db)
                except Exception as _ev_exc:
                    logger.warning("evolution_cycle_error", error=str(_ev_exc))

        asyncio.ensure_future(_evolution_loop())
        logger.info("skill_evolution_loop_started", interval_seconds=600)
    except Exception as exc:
        logger.warning("skill_evolution_loop_warning", error=str(exc))

    # ── Obsidian Vault Integration ─────────────────────────────────────────────
    try:
        from app.obsidian.sync import get_obsidian, register_hooks
        get_obsidian()   # initialise singleton (reads OBSIDIAN_VAULT_PATH env)
        register_hooks() # attach to orchestrator + self-improvement loop
        logger.info("obsidian_initialized")
    except Exception as exc:
        logger.warning("obsidian_init_warning", error=str(exc))

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
app.include_router(self_evolution_router.self_improvement_router)
# local_actions merged into tools.router above

# Persistent services — memory, skills, profile, agent loop, scheduler
app.include_router(skills.router)
app.include_router(profile.router)
app.include_router(agent.router)
app.include_router(scheduler_router.router)

# Brain architecture
app.include_router(brain_router)

# Evolution & self-improvement
app.include_router(evolution_router)

# Code indexing (Phase 1)
app.include_router(code_indexing_router)

# Workflows (Phase 2)
app.include_router(workflows_router)

# Device Agent (Phase 3)
app.include_router(device_agent_router)

# Cognitive Reasoning (Phase 4)
app.include_router(reasoning_router)

# Provider Discovery & Health (Phase 5)
app.include_router(provider_discovery_router)

# Image Generation (Phase 6)
app.include_router(image_generation_router)

# Prompt Mutation Engine (Phase 7)
app.include_router(prompt_mutation_router)

# External API Registry
app.include_router(external_apis_router.router)

# Workflow Engine (Ruflo) — new execution layer
app.include_router(workflows_engine_router.router)

# Swarm Manager (v3 Distributed Autonomous Swarm Intelligence)
app.include_router(swarm_manager_router.router)

# Memory Fabric (v3 Multi-Layered Cognitive Memory) — merged into memory.py
app.include_router(memory.memory_fabric_router)

# Self-Evolution Engine (v3 Self-Improvement)
app.include_router(self_evolution_router.router)

# Multi-Agent Orchestration
app.include_router(orchestrate_router)

# STT (faster-whisper GPU)
app.include_router(stt_router.router)

# ── Skill Marketplace (Skill OS) ──────────────────────────────────────────────
from app.routers.marketplace import router as marketplace_router
app.include_router(marketplace_router)

from app.routers.multi_agent import router as multi_agent_router
app.include_router(multi_agent_router)

# ── Approval Gates ────────────────────────────────────────────────────────────
from app.routers.approval import router as approval_router
app.include_router(approval_router)

# ── Prompt Library ────────────────────────────────────────────────────────────
from app.routers.prompt_library import router as prompt_library_router
app.include_router(prompt_library_router)

# ── Wake Word endpoints (part of voice) ──────────────────────────────────────
from app.routers import wake_word as wake_word_router
app.include_router(wake_word_router.router)

# ── Obsidian Vault Integration ────────────────────────────────────────────────
from app.routers.obsidian import router as obsidian_router
app.include_router(obsidian_router)
