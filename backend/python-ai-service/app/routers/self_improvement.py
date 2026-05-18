from __future__ import annotations

import json
import os
import time
from uuid import uuid4

import redis.asyncio as aioredis
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.core.config import get_settings
from app.core.envelopes import error, success
from app.core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()

# ── Redis keys ────────────────────────────────────────────────────────────────
_KEY_PENDING = "jarvis:self_improvement:pending"
_KEY_APPLIED = "jarvis:self_improvement:applied"


def _redis_url() -> str:
    return os.getenv("REDIS_URL", "redis://localhost:6379/0")


async def _get_redis() -> aioredis.Redis:
    return await aioredis.from_url(_redis_url(), decode_responses=True)


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _load_list(key: str) -> list[dict]:
    try:
        r = await _get_redis()
        items = await r.lrange(key, 0, -1)
        await r.aclose()
        return [json.loads(i) for i in items]
    except Exception as exc:
        logger.warning("self_improvement_redis_read_failed", key=key, error=str(exc))
        return []


async def _push(key: str, item: dict) -> None:
    try:
        r = await _get_redis()
        await r.rpush(key, json.dumps(item))
        await r.aclose()
    except Exception as exc:
        logger.warning("self_improvement_redis_write_failed", key=key, error=str(exc))


async def _remove_by_id(key: str, suggestion_id: str) -> dict | None:
    """Remove and return the first item matching suggestion_id."""
    try:
        r = await _get_redis()
        items = await r.lrange(key, 0, -1)
        for raw in items:
            item = json.loads(raw)
            if item.get("id") == suggestion_id:
                await r.lrem(key, 1, raw)
                await r.aclose()
                return item
        await r.aclose()
    except Exception as exc:
        logger.warning("self_improvement_redis_remove_failed", error=str(exc))
    return None


# ── Routes ────────────────────────────────────────────────────────────────────

@router.get("/self-improvement/status")
async def status(request: Request) -> dict:
    correlation_id = request.headers.get("x-correlation-id")
    settings = get_settings()
    pending = await _load_list(_KEY_PENDING)
    applied = await _load_list(_KEY_APPLIED)
    return success(
        {
            "enabled": settings.self_improvement_enabled,
            "requireApproval": settings.self_improvement_require_approval,
            "versioningEnabled": settings.self_versioning_enabled,
            "pendingSuggestions": len(pending),
            "appliedCount": len(applied),
        },
        correlation_id,
    )


@router.get("/self-improvement/suggestions")
async def list_suggestions(request: Request) -> dict:
    correlation_id = request.headers.get("x-correlation-id")
    suggestions = await _load_list(_KEY_PENDING)
    return success({"suggestions": suggestions, "total": len(suggestions)}, correlation_id)


@router.post("/self-improvement/suggest")
async def create_suggestion(request: Request) -> dict:
    """
    Ask the active provider to generate a self-improvement suggestion.
    Suggestions are persisted in Redis and require human approval.
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

    # Get a real suggestion from the active provider
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

    await _push(_KEY_PENDING, suggestion)
    logger.info("self_improvement_suggestion_created", suggestion_id=suggestion_id)
    return success(suggestion, correlation_id)


@router.post("/self-improvement/suggestions/{suggestion_id}/approve")
async def approve_suggestion(suggestion_id: str, request: Request) -> dict:
    correlation_id = request.headers.get("x-correlation-id")
    suggestion = await _remove_by_id(_KEY_PENDING, suggestion_id)
    if not suggestion:
        return JSONResponse(
            status_code=404,
            content=error("not_found", f"Suggestion '{suggestion_id}' not found", correlation_id=correlation_id),
        )

    suggestion["status"] = "approved"
    suggestion["approvedAt"] = time.time()
    await _push(_KEY_APPLIED, suggestion)
    logger.info("self_improvement_approved", suggestion_id=suggestion_id)
    return success({"approved": True, "suggestionId": suggestion_id}, correlation_id)


@router.post("/self-improvement/suggestions/{suggestion_id}/reject")
async def reject_suggestion(suggestion_id: str, request: Request) -> dict:
    correlation_id = request.headers.get("x-correlation-id")
    suggestion = await _remove_by_id(_KEY_PENDING, suggestion_id)
    if not suggestion:
        return JSONResponse(
            status_code=404,
            content=error("not_found", f"Suggestion '{suggestion_id}' not found", correlation_id=correlation_id),
        )
    logger.info("self_improvement_rejected", suggestion_id=suggestion_id)
    return success({"rejected": True, "suggestionId": suggestion_id}, correlation_id)
