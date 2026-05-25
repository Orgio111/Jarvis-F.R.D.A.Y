"""API routes for the Self-Evolution Engine — continuous self-improvement."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query

from fastapi.responses import JSONResponse

from app.core.envelopes import success, error

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
