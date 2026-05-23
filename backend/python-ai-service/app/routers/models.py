from __future__ import annotations

from fastapi import APIRouter, Request

from app.core.envelopes import success
from app.core.logging import get_logger
from app.core.model_modes import ALL_MODES, MODES_DISPLAY, MODES_DESCRIPTION, compute_mode_availability
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


@router.get("/models/modes")
async def list_model_modes(request: Request) -> dict:
    """Return all model modes with their resolved models and availability."""
    correlation_id = request.headers.get("x-correlation-id")
    try:
        pr = ProviderRouter.get()
        all_models = await pr.get_all_models()
        availability = compute_mode_availability(all_models)
    except Exception as exc:
        logger.error("list_model_modes_failed", error=str(exc))
        availability = []

    return success(
        {
            "modes": [
                {
                    "mode": a.mode,
                    "displayName": a.displayName,
                    "description": a.description,
                    "resolved": {
                        "modelId": a.resolved.modelId,
                        "providerId": a.resolved.providerId,
                        "providerName": a.resolved.providerName,
                        "modelName": a.resolved.modelName,
                    } if a.resolved else None,
                    "availableModels": [
                        {
                            "id": m["id"],
                            "name": m["name"],
                            "providerId": m.get("providerId", ""),
                            "providerName": m.get("providerName", ""),
                            "groups": m.get("groups", []),
                            "isFree": m.get("isFree", False),
                        }
                        for m in a.availableModels
                    ],
                }
                for a in availability
            ]
        },
        correlation_id,
    )
