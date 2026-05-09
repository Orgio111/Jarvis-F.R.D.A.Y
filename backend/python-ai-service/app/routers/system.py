from __future__ import annotations

import time

from fastapi import APIRouter, Request

from app.core.config import get_settings
from app.core.envelopes import success
from app.core.logging import get_logger
from app.gpu.detector import GPUDetector

logger = get_logger(__name__)
router = APIRouter()

_start_time = time.time()


@router.get("/system/status")
async def system_status(request: Request) -> dict:
    correlation_id = request.headers.get("x-correlation-id")
    settings = get_settings()
    info = GPUDetector.get_info()

    uptime_s = time.time() - _start_time

    components = {
        "python-ai-service": {"name": "python-ai-service", "status": "ok"},
        "gpu": {
            "name": "gpu",
            "status": "ok" if info.cuda_available else "warn",
            "message": "GPU not available; using CPU" if not info.cuda_available else None,
        },
    }

    return success(
        {
            "status": "healthy",
            "version": "0.1.0",
            "appEnv": settings.app_env,
            "uptime": f"{round(uptime_s)}s",
            "startedAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(time.time() - uptime_s)),
            "components": components,
        },
        correlation_id,
    )


@router.get("/system/metrics")
async def system_metrics(request: Request) -> dict:
    correlation_id = request.headers.get("x-correlation-id")
    return success(
        {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "cpuPercent": 0.0,
            "memPercent": 0.0,
            "memUsedMb": 0,
            "memTotalMb": 0,
            "diskPercent": 0.0,
            "requestsPerSecond": 0.0,
            "errorsPerSecond": 0.0,
            "p99LatencyMs": 0.0,
        },
        correlation_id,
    )
