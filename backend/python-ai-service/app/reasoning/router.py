"""
Reasoning Engine API router.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.reasoning.engine import ReasoningEngine, ReasoningStrategy, get_engine

router = APIRouter(prefix="/reasoning", tags=["reasoning"])


class ReasonRequest(BaseModel):
    query: str
    strategy: str = "chain_of_thought"  # direct, chain_of_thought, tree_of_thought, self_verification, decomposition, multi_perspective
    context: str = ""
    max_depth: int = 3


class ReasonResponse(BaseModel):
    traceId: str
    query: str
    strategy: str
    conclusion: str
    finalConfidence: float
    durationMs: float
    nodeCount: int


@router.post("/reason", response_model=ReasonResponse)
async def reason(req: ReasonRequest):
    """Execute a reasoning process using the specified strategy."""
    engine = get_engine()

    try:
        strategy = ReasoningStrategy(req.strategy)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid strategy '{req.strategy}'. Options: {[s.value for s in ReasoningStrategy]}",
        )

    trace = await engine.reason(
        query=req.query,
        strategy=strategy,
        context=req.context,
        max_depth=min(req.max_depth, 5),
    )

    return ReasonResponse(
        traceId=trace.id,
        query=trace.query[:200],
        strategy=trace.strategy.value,
        conclusion=trace.conclusion or "",
        finalConfidence=trace.final_confidence,
        durationMs=trace.duration_ms,
        nodeCount=len(trace.nodes),
    )


@router.get("/traces/{trace_id}")
async def get_trace(trace_id: str):
    """Get a specific reasoning trace."""
    engine = get_engine()
    trace = await engine.get_trace(trace_id)
    if not trace:
        raise HTTPException(status_code=404, detail="Trace not found")
    return trace.to_dict()


@router.get("/traces")
async def list_traces(limit: int = 20):
    """List recent reasoning traces."""
    engine = get_engine()
    return await engine.list_traces(limit=min(limit, 100))
