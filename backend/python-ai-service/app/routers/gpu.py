from __future__ import annotations

import time

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.core.config import get_settings
from app.core.envelopes import success, error
from app.core.logging import get_logger
from app.gpu.detector import GPUDetector
from app.gpu.workload_router import WorkloadRouter

logger = get_logger(__name__)
router = APIRouter()

_workload_router: WorkloadRouter | None = None


def set_workload_router(wr: WorkloadRouter) -> None:
    global _workload_router
    _workload_router = wr


def _build_gpu_status() -> dict:
    settings = get_settings()
    info = GPUDetector.get_info()
    wr = _workload_router

    # VRAM info for first device
    vram = {"totalMb": 0, "usedMb": 0, "freeMb": 0}
    active_device = "cpu"
    driver_version = None
    cuda_version = info.cuda_version

    if info.cuda_available and info.devices:
        dev = info.devices[0]
        vram["totalMb"] = dev.get("totalMemoryMb", 0)
        active_device = f"cuda:0 ({dev.get('name', 'Unknown')})"
        # Try to get live usage
        try:
            import torch  # type: ignore
            mem = torch.cuda.memory_stats(0)
            allocated = mem.get("allocated_bytes.all.current", 0)
            vram["usedMb"] = allocated // (1024 * 1024)
            vram["freeMb"] = vram["totalMb"] - vram["usedMb"]
        except Exception:
            pass

    fallback_active = not info.cuda_available and settings.gpu_allow_cpu_fallback
    fallback_reason = None
    if fallback_active:
        fallback_reason = "CUDA not available; using CPU fallback"
    elif not settings.gpu_enabled:
        fallback_reason = "GPU disabled by configuration"

    workloads = wr.get_workloads() if wr else {
        "localLlm": "cpu", "stt": "cpu", "tts": "cpu",
        "embeddings": "cpu", "faiss": "cpu", "vision": "cpu",
        "rag": "cpu", "memorySynthesis": "cpu",
    }

    return {
        "enabled": settings.gpu_enabled,
        "available": info.cuda_available,
        "required": settings.gpu_required,
        "provider": settings.gpu_provider if info.cuda_available else "none",
        "deviceCount": info.device_count,
        "activeDevice": active_device,
        "cudaAvailable": info.cuda_available,
        "cudaVersion": cuda_version,
        "driverVersion": driver_version,
        "vram": vram,
        "utilization": {
            "gpuPercent": 0.0,
            "memoryPercent": round((vram["usedMb"] / vram["totalMb"] * 100) if vram["totalMb"] else 0.0, 1),
            "temperatureC": 0.0,
            "powerWatts": 0.0,
        },
        "workloads": workloads,
        "fallback": {
            "cpuFallbackAllowed": settings.gpu_allow_cpu_fallback,
            "cpuFallbackActive": fallback_active,
            "reason": fallback_reason,
        },
    }


@router.get("/gpu/status")
async def gpu_status(request: Request) -> dict:
    correlation_id = request.headers.get("x-correlation-id")
    return success(_build_gpu_status(), correlation_id)


@router.get("/gpu/metrics")
async def gpu_metrics(request: Request) -> dict:
    correlation_id = request.headers.get("x-correlation-id")
    metrics = []
    info = GPUDetector.get_info()
    if info.cuda_available:
        for dev in info.devices:
            metrics.append(
                {
                    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                    "deviceIndex": dev["index"],
                    "deviceName": dev.get("name", "unknown"),
                    "utilization": {"gpuPercent": 0.0, "memoryPercent": 0.0, "temperatureC": 0.0, "powerWatts": 0.0},
                    "vram": {
                        "totalMb": dev.get("totalMemoryMb", 0),
                        "usedMb": 0,
                        "freeMb": dev.get("totalMemoryMb", 0),
                    },
                }
            )
    return success(metrics, correlation_id)


@router.post("/gpu/workloads/reload")
async def reload_workloads(request: Request) -> dict:
    correlation_id = request.headers.get("x-correlation-id")
    global _workload_router
    settings = get_settings()
    _workload_router = WorkloadRouter(settings)
    return success({"reloaded": True, "workloads": _workload_router.get_workloads()}, correlation_id)


@router.patch("/gpu/settings")
async def patch_gpu_settings(request: Request) -> dict:
    correlation_id = request.headers.get("x-correlation-id")
    body = await request.json()
    return success({"updated": True, "settings": body}, correlation_id)
