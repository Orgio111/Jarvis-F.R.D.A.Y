from __future__ import annotations

import time

from fastapi import APIRouter, Request

from app.core.config import get_settings
from app.core.envelopes import success
from app.core.logging import get_logger
from app.gpu.detector import GPUDetector
from app.gpu.workload_router import WorkloadRouter
from app.providers.router import ProviderRouter

logger = get_logger(__name__)
router = APIRouter()

_start_time = time.time()


@router.get("/bootstrap")
async def bootstrap(request: Request) -> dict:
    correlation_id = request.headers.get("x-correlation-id")
    settings = get_settings()
    gpu_info = GPUDetector.get_info()

    # Provider statuses
    try:
        provider_router = ProviderRouter.get()
        provider_statuses = await provider_router.get_all_statuses()
    except Exception:
        provider_statuses = []

    available_providers = [p for p in provider_statuses if p["status"] == "available"]
    primary_status = next((p for p in provider_statuses if p["id"] == settings.ai_provider_primary), {
        "id": settings.ai_provider_primary,
        "name": "NVIDIA NIM",
        "status": "provider_unavailable",
        "reason": "not initialised",
        "deviceMode": "disabled",
        "modelCount": 0,
    })
    fallback_status = next((p for p in provider_statuses if p["id"] == settings.ai_provider_fallback), {
        "id": settings.ai_provider_fallback,
        "name": "OpenRouter",
        "status": "provider_unavailable",
        "reason": "not initialised",
        "deviceMode": "disabled",
        "modelCount": 0,
    })

    # GPU status (inline — mirrors /gpu/status)
    from app.routers.gpu import _build_gpu_status
    gpu_status = _build_gpu_status()

    uptime_s = time.time() - _start_time
    system_status = "healthy" if available_providers else "degraded"

    data = {
        "system": {
            "appName": settings.app_name,
            "appEnv": settings.app_env,
            "version": "0.1.0",
            "apiVersion": "v1",
            "uptime": f"{round(uptime_s)}s",
            "status": system_status,
        },
        "providers": {
            "primary": primary_status,
            "fallback": fallback_status,
            "available": available_providers,
        },
        "models": {
            "defaultChatModel": "",
            "defaultCoderModel": "",
            "defaultFastModel": "",
            "totalAvailable": 0,
            "discoveryEnabled": settings.model_discovery_enabled,
        },
        "settings": {
            "theme": "dark",
            "language": "en",
            "streamingEnabled": True,
        },
        "voice": {
            "sttEnabled": settings.stt_enabled,
            "ttsEnabled": settings.tts_enabled,
            "sttEngine": settings.stt_engine,
            "ttsEngine": settings.tts_engine,
            "sttDeviceMode": "gpu" if (settings.stt_gpu_enabled and gpu_info.cuda_available) else "cpu",
            "ttsDeviceMode": "cpu",
        },
        "features": {
            "chat": True,
            "voice": settings.stt_enabled or settings.tts_enabled,
            "vision": settings.vision_enabled,
            "terminal": True,
            "memory": settings.faiss_enabled,
            "tools": True,
            "execution": settings.sandbox_enabled,
            "search": settings.web_search_enabled,
            "localControl": settings.local_pc_control_enabled,
            "selfImprovement": settings.self_improvement_enabled,
            "localLlm": settings.local_llm_enabled,
            "gpuMonitor": settings.gpu_enabled,
        },
        "gpu": gpu_status,
    }

    return success(data, correlation_id)
