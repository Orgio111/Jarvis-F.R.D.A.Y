from __future__ import annotations

from fastapi import APIRouter, Request

from app.core.envelopes import success
from app.core.logging import get_logger
from app.providers.router import ProviderRouter

logger = get_logger(__name__)
router = APIRouter()


@router.get("/models")
async def list_models(request: Request, provider: str | None = None) -> dict:
    correlation_id = request.headers.get("x-correlation-id")
    try:
        pr = ProviderRouter.get()
        if provider:
            p = pr.get_provider(provider)
            models = await p.list_models() if p else []
        else:
            models = await pr.get_all_models()
    except Exception as exc:
        logger.error("list_models_failed", error=str(exc))
        models = []

    return success(
        {
            "models": models,
            "total": len(models),
        },
        correlation_id,
    )
