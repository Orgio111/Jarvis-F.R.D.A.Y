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
            },
            correlation_id,
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("get_provider_failed", provider_id=provider_id, error=str(exc))
        return error("provider_error", str(exc), correlation_id=correlation_id)
