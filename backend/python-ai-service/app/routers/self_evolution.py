"""API routes for the Self-Evolution Engine + Self-Improvement (merged)."""

from __future__ import annotations

import json
import os
import time
from typing import Any
from uuid import uuid4

import redis.asyncio as aioredis
from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import JSONResponse

from app.core.config import get_settings
from app.core.envelopes import success, error
from app.core.logging import get_logger

logger = get_logger(__name__)

# ─── Router: Evolution Engine (v3) ────────────────────────────────────────────

router = APIRouter(prefix="/evolution", tags=["evolution"])


def _get_service():
    try:
        from app.services.self_evolution_service import SelfEvolutionService
        return SelfEvolutionService.get()
    except RuntimeError:
        raise HTTPException(status_code=503, detail="SelfEvolutionService not initialized")


@router.get("/status")
async def get_evolution_status() -> dict[str, Any]:
    """Get evolution engine status."""
    svc = _get_service()
    return success(svc.get_status())


@router.get("/trials")
async def get_trials(
    limit: int = Query(50, ge=1, le=200),
) -> dict[str, Any]:
    """Get recent evolution trials."""
    svc = _get_service()
    return success({"trials": svc.get_trials(limit=limit)})


@router.get("/best-practices")
async def get_best_practices(
    limit: int = Query(5, ge=1, le=20),
) -> dict[str, Any]:
    """Get most successful mutations as best practices."""
    svc = _get_service()
    return success({"bestPractices": svc.get_best_practices(limit=limit)})


@router.post("/propose")
async def propose_mutation(
    mutation_type: str,
    target: str,
    current_value: Any,
) -> dict[str, Any]:
    """Propose a mutation for a given target."""
    svc = _get_service()
    result = svc.propose_mutation(mutation_type, target, current_value)
    if not result.get("success"):
        return JSONResponse(status_code=400, content=error("mutation_failed", result.get("error", "Mutation failed")))
    return success(result)


@router.post("/trial")
async def run_trial(
    mutation_type: str,
    target: str,
    original_value: Any,
    mutated_value: Any,
    correctness: float = 0.0,
    completeness: float = 0.0,
    efficiency: float = 0.0,
    confidence: float = 0.0,
    latency_ms: float = 0.0,
    cost: float = 0.0,
) -> dict[str, Any]:
    """Run an evolution trial."""
    svc = _get_service()
    result = svc.run_trial(
        mutation_type=mutation_type,
        target=target,
        original_value=original_value,
        mutated_value=mutated_value,
        correctness=correctness,
        completeness=completeness,
        efficiency=efficiency,
        confidence=confidence,
        latency_ms=latency_ms,
        cost=cost,
    )
    if not result.get("success"):
        return JSONResponse(status_code=400, content=error("trial_failed", result.get("error", "Trial failed")))
    return success(result)


@router.get("/should-mutate")
async def should_mutate(current_score: float) -> dict[str, Any]:
    """Check if a mutation should be attempted."""
    svc = _get_service()
    return success(svc.should_mutate(current_score))


# ─── Router: Self-Improvement Suggestions (merged from self_improvement.py) ────

self_improvement_router = APIRouter(tags=["self-improvement"])

# Redis keys
_KEY_PENDING = "jarvis:self_improvement:pending"
_KEY_APPLIED = "jarvis:self_improvement:applied"


def _redis_url() -> str:
    return os.getenv("REDIS_URL", "redis://localhost:6379/0")


async def _get_redis() -> aioredis.Redis:
    return await aioredis.from_url(_redis_url(), decode_responses=True)


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


@self_improvement_router.get("/self-improvement/status")
async def si_status(request: Request) -> dict:
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


@self_improvement_router.get("/self-improvement/suggestions")
async def si_list_suggestions(request: Request) -> dict:
    correlation_id = request.headers.get("x-correlation-id")
    suggestions = await _load_list(_KEY_PENDING)
    return success({"suggestions": suggestions, "total": len(suggestions)}, correlation_id)


@self_improvement_router.post("/self-improvement/suggest")
async def si_create_suggestion(request: Request) -> dict:
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


@self_improvement_router.post("/self-improvement/suggestions/{suggestion_id}/approve")
async def si_approve_suggestion(suggestion_id: str, request: Request) -> dict:
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


@self_improvement_router.post("/self-improvement/suggestions/{suggestion_id}/reject")
async def si_reject_suggestion(suggestion_id: str, request: Request) -> dict:
    correlation_id = request.headers.get("x-correlation-id")
    suggestion = await _remove_by_id(_KEY_PENDING, suggestion_id)
    if not suggestion:
        return JSONResponse(
            status_code=404,
            content=error("not_found", f"Suggestion '{suggestion_id}' not found", correlation_id=correlation_id),
        )
    logger.info("self_improvement_rejected", suggestion_id=suggestion_id)
    return success({"rejected": True, "suggestionId": suggestion_id}, correlation_id)
