from __future__ import annotations

import base64

from fastapi import APIRouter, File, Request, UploadFile
from fastapi.responses import JSONResponse

from app.core.config import get_settings
from app.core.envelopes import error, success
from app.core.logging import get_logger
from app.providers.router import ProviderRouter

logger = get_logger(__name__)
router = APIRouter()


def _get_wr():
    """Lazy import to avoid circular deps at module load time."""
    from app.routers.gpu import get_workload_router
    return get_workload_router()


@router.post("/vision/analyze")
async def analyze_image(
    request: Request,
    image: UploadFile = File(...),
) -> dict:
    """
    Analyze an uploaded image via the active provider's vision model.
    Falls back to a safe 'vision_unavailable' response if the provider
    doesn't support vision or the image can't be processed.
    """
    correlation_id = request.headers.get("x-correlation-id")
    settings = get_settings()

    if not settings.vision_enabled:
        return JSONResponse(
            status_code=503,
            content=error("vision_disabled", "Vision is disabled", correlation_id=correlation_id),
        )

    prompt: str = request.headers.get("x-vision-prompt", "Describe this image in detail.")

    try:
        image_bytes = await image.read()
        if len(image_bytes) > 20 * 1024 * 1024:  # 20 MB limit
            return JSONResponse(
                status_code=413,
                content=error("image_too_large", "Image must be under 20 MB", correlation_id=correlation_id),
            )

        content_type = image.content_type or "image/jpeg"
        b64 = base64.b64encode(image_bytes).decode()
        data_url = f"data:{content_type};base64,{b64}"

        # Build the OpenAI-compatible vision message
        vision_messages = [
            {
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": data_url}},
                    {"type": "text", "text": prompt},
                ],
            }
        ]

        try:
            pr = ProviderRouter.get()
            provider = pr.get_active_provider()
            if provider is None:
                return _vision_unavailable(correlation_id, "No AI provider available")
        except Exception as exc:
            return _vision_unavailable(correlation_id, str(exc))

        # Acquire a GPU semaphore slot so concurrent vision calls can't OOM the GPU.
        # If WorkloadRouter isn't ready yet (early lifespan), we skip the semaphore.
        wr = _get_wr()

        async def _do_vision():
            result = await provider.chat(
                messages=vision_messages,
                model_id=settings.default_chat_model or "",
                max_tokens=512,
            )
            return result

        # Try chat with the vision message
        try:
            if wr is not None:
                async with wr.acquire("vision"):
                    result = await _do_vision()
            else:
                result = await _do_vision()

            content = _extract_content(result)
            return success(
                {
                    "description": content,
                    "model": result.get("model", "unknown"),
                    "providerId": provider.provider_id,
                    "imageSize": len(image_bytes),
                    "contentType": content_type,
                },
                correlation_id,
            )
        except Exception as exc:
            logger.warning("vision_provider_failed", error=str(exc))
            return _vision_unavailable(correlation_id, f"Provider error: {exc}")

    except Exception as exc:
        logger.error("vision_analyze_failed", error=str(exc))
        return JSONResponse(
            status_code=500,
            content=error("vision_error", str(exc), correlation_id=correlation_id),
        )


@router.get("/vision/status")
async def vision_status(request: Request) -> dict:
    correlation_id = request.headers.get("x-correlation-id")
    settings = get_settings()

    provider_supports_vision = False
    try:
        pr = ProviderRouter.get()
        provider = pr.get_active_provider()
        if provider:
            models = await provider.list_models()
            provider_supports_vision = any(m.get("supportsVision") for m in models)
    except Exception:
        pass

    return success(
        {
            "enabled": settings.vision_enabled,
            "providerSupportsVision": provider_supports_vision,
            "maxImageSizeMb": 20,
        },
        correlation_id,
    )


def _vision_unavailable(correlation_id: str | None, reason: str) -> JSONResponse:
    return JSONResponse(
        status_code=503,
        content=error("vision_unavailable", reason, correlation_id=correlation_id),
    )


def _extract_content(result: dict) -> str:
    try:
        return result["choices"][0]["message"]["content"] or ""
    except (KeyError, IndexError):
        return ""
