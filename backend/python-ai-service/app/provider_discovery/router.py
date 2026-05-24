"""Provider Discovery API router."""

from __future__ import annotations

from fastapi import APIRouter

from app.provider_discovery.discovery import get_discoverer
from app.provider_discovery.health_monitor import get_health_monitor

router = APIRouter(prefix="/providers/discovery", tags=["provider-discovery"])


@router.get("/discover")
async def discover_providers():
    """Run provider discovery — scan and health-check all known providers."""
    discoverer = get_discoverer()
    endpoints = await discoverer.discover_all()
    return {
        "providers": [
            {
                "name": e.name,
                "baseUrl": e.base_url,
                "apiType": e.api_type,
                "isAvailable": e.is_available,
                "isFree": e.is_free,
                "latencyMs": round(e.latency_ms, 1),
                "score": round(e.score, 1),
                "modelCount": len(e.models),
                "capabilities": list(e.capabilities),
            }
            for e in endpoints
        ],
        "total": len(endpoints),
        "available": sum(1 for e in endpoints if e.is_available),
    }


@router.get("/best")
async def best_providers(capability: str | None = None, limit: int = 3):
    """Get the best available providers, optionally by capability."""
    discoverer = get_discoverer()
    best = await discoverer.get_best_providers(capability=capability, limit=limit)
    return {
        "providers": [
            {
                "name": e.name,
                "baseUrl": e.base_url,
                "score": round(e.score, 1),
                "latencyMs": round(e.latency_ms, 1),
                "capabilities": list(e.capabilities),
            }
            for e in best
        ]
    }


@router.get("/health")
async def health_status():
    """Get health status of all registered providers."""
    monitor = get_health_monitor()
    return {
        "providers": monitor.get_all_statuses(),
        "available": monitor.get_available(),
    }


@router.post("/health/start")
async def start_health_monitoring(interval: int = 60):
    """Start continuous provider health monitoring."""
    monitor = get_health_monitor()
    await monitor.start(interval=interval)
    return {"status": "started", "interval": interval}


@router.post("/health/stop")
async def stop_health_monitoring():
    """Stop provider health monitoring."""
    monitor = get_health_monitor()
    await monitor.stop()
    return {"status": "stopped"}
