from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from app.core.envelopes import error, success
from app.core.logging import get_logger
from app.providers.router import ProviderRouter

logger = get_logger(__name__)
router = APIRouter()


@router.get("/providers")
async def list_providers(request: Request) -> dict:
    correlation_id = request.headers.get("x-correlation-id")
    try:
        pr = ProviderRouter.get()
        statuses = await pr.get_all_statuses()
    except Exception as exc:
        logger.error("list_providers_failed", error=str(exc))
        return success([], correlation_id)
    return success(statuses, correlation_id)


@router.get("/providers/discovered")
async def list_discovered_providers(request: Request) -> dict:
    """List only dynamically discovered providers with rich metadata."""
    correlation_id = request.headers.get("x-correlation-id")
    try:
        pr = ProviderRouter.get()
        discovered = pr.get_discovered_providers()
        result = []
        for p in discovered:
            health = await p.health_check()
            summary = getattr(p, "get_endpoint_summary", lambda: {})()
            result.append({
                "id": p.provider_id,
                "name": p.provider_name,
                "status": health["status"],
                "reason": health.get("reason"),
                "deviceMode": p.device_mode,
                "isDefault": False,
                "isFallback": False,
                "isDiscovered": True,
                "latencyMs": summary.get("latencyMs", 0),
                "score": summary.get("score", 0),
                "modelCount": summary.get("modelCount", 0),
                "capabilities": summary.get("capabilities", []),
                "isFree": summary.get("isFree", False),
                "baseUrl": summary.get("baseUrl", ""),
                "models": summary.get("models", []),
            })
    except Exception as exc:
        logger.error("list_discovered_failed", error=str(exc))
        return success([], correlation_id)
    return success(result, correlation_id)


@router.post("/providers/discover/sync")
async def sync_discovered_providers(request: Request) -> dict:
    """Manually trigger provider discovery and sync discovered providers into the router."""
    correlation_id = request.headers.get("x-correlation-id")
    try:
        pr = ProviderRouter.get()
        count = await pr.sync_discovered()
        return success({"synced": count}, correlation_id)
    except Exception as exc:
        logger.error("sync_discovered_failed", error=str(exc))
        return error("sync_error", str(exc), correlation_id=correlation_id)


@router.get("/providers/{provider_id}")
async def get_provider(provider_id: str, request: Request) -> dict:
    correlation_id = request.headers.get("x-correlation-id")
    try:
        pr = ProviderRouter.get()
        provider = pr.get_provider(provider_id)
        if provider is None:
            raise HTTPException(status_code=404, detail=f"Provider '{provider_id}' not found")
        health = await provider.health_check()
        return success(
            {
                "id": provider.provider_id,
                "name": provider.provider_name,
                "status": health["status"],
                "reason": health.get("reason"),
                "deviceMode": provider.device_mode,
                "isDiscovered": provider.provider_id.startswith("discovered:"),
            },
            correlation_id,
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("get_provider_failed", provider_id=provider_id, error=str(exc))
        return error("provider_error", str(exc), correlation_id=correlation_id)
