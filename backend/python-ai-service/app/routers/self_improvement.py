from __future__ import annotations

import time
from uuid import uuid4

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.core.config import get_settings
from app.core.envelopes import error, success
from app.core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()

# In-memory suggestion log (volatile — for demo/development)
_suggestions: list[dict] = []
_applied: list[dict] = []


@router.get("/self-improvement/status")
async def status(request: Request) -> dict:
    correlation_id = request.headers.get("x-correlation-id")
    settings = get_settings()
    return success(
        {
            "enabled": settings.self_improvement_enabled,
            "requireApproval": settings.self_improvement_require_approval,
            "versioningEnabled": settings.self_versioning_enabled,
            "pendingSuggestions": len(_suggestions),
            "appliedCount": len(_applied),
        },
        correlation_id,
    )


@router.get("/self-improvement/suggestions")
async def list_suggestions(request: Request) -> dict:
    correlation_id = request.headers.get("x-correlation-id")
    return success({"suggestions": _suggestions, "total": len(_suggestions)}, correlation_id)


@router.post("/self-improvement/suggest")
async def create_suggestion(request: Request) -> dict:
    """
    Ask the active provider to generate a self-improvement suggestion
    based on recent conversation context or a provided prompt.
    Suggestions are queued and require human approval before being applied.
    """
    correlation_id = request.headers.get("x-correlation-id")
    settings = get_settings()

    if not settings.self_improvement_enabled:
        return JSONResponse(
            status_code=503,
            content=error("self_improvement_disabled", "Self-improvement is disabled", correlation_id=correlation_id),
        )

    try:
        body = await request.json()
    except Exception:
        return JSONResponse(
            status_code=400,
            content=error("invalid_request", "Request body must be valid JSON", correlation_id=correlation_id),
        )

    context: str = body.get("context", "").strip()
    if not context:
        return JSONResponse(
            status_code=400,
            content=error("invalid_request", "context is required", correlation_id=correlation_id),
        )

    suggestion_id = f"sug_{uuid4().hex[:8]}"
    suggestion = {
        "id": suggestion_id,
        "context": context[:1000],
        "suggestion": f"[Pending AI analysis of: {context[:80]}…]",
        "status": "pending_review",
        "createdAt": time.time(),
        "requiresApproval": settings.self_improvement_require_approval,
    }

    # Attempt to get a real suggestion from the provider
    try:
        from app.providers.router import ProviderRouter
        pr = ProviderRouter.get()
        provider = pr.get_active_provider()
        if provider:
            result = await provider.chat(
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are JARVIS's self-improvement module. "
                            "Analyze the provided context and suggest ONE concrete, actionable "
                            "improvement. Be specific: what to change, why, and expected impact. "
                            "Reply in 2-4 sentences."
                        ),
                    },
                    {"role": "user", "content": context},
                ],
                model_id="",
                max_tokens=256,
            )
            content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
            if content:
                suggestion["suggestion"] = content.strip()
    except Exception as exc:
        logger.warning("self_improvement_ai_failed", error=str(exc))

    _suggestions.append(suggestion)
    return success(suggestion, correlation_id)


@router.post("/self-improvement/suggestions/{suggestion_id}/approve")
async def approve_suggestion(suggestion_id: str, request: Request) -> dict:
    correlation_id = request.headers.get("x-correlation-id")
    suggestion = next((s for s in _suggestions if s["id"] == suggestion_id), None)
    if not suggestion:
        return JSONResponse(
            status_code=404,
            content=error("not_found", f"Suggestion '{suggestion_id}' not found", correlation_id=correlation_id),
        )

    suggestion["status"] = "approved"
    _applied.append(suggestion)
    _suggestions.remove(suggestion)
    logger.info("self_improvement_approved", suggestion_id=suggestion_id)
    return success({"approved": True, "suggestionId": suggestion_id}, correlation_id)


@router.post("/self-improvement/suggestions/{suggestion_id}/reject")
async def reject_suggestion(suggestion_id: str, request: Request) -> dict:
    correlation_id = request.headers.get("x-correlation-id")
    suggestion = next((s for s in _suggestions if s["id"] == suggestion_id), None)
    if not suggestion:
        return JSONResponse(
            status_code=404,
            content=error("not_found", f"Suggestion '{suggestion_id}' not found", correlation_id=correlation_id),
        )
    suggestion["status"] = "rejected"
    _suggestions.remove(suggestion)
    return success({"rejected": True, "suggestionId": suggestion_id}, correlation_id)
