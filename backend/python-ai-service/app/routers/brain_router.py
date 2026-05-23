"""
Brain Router — REST API for the full cognitive architecture.

Endpoints:
  GET    /brain/status          — System-wide brain status
  GET    /brain/sectors         — List all available sector brains
  POST   /brain/process         — Process a task through the Macro Brain
  POST   /brain/plan            — Generate a strategy plan
  GET    /brain/reputation      — Agent reputation rankings
  GET    /brain/routing         — Smart Router history and analysis
  POST   /brain/sector/{id}     — Directly invoke a specific sector brain
"""
from __future__ import annotations

import json

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, StreamingResponse

from app.brain.macro_brain import MacroBrain
from app.brain.strategy_brain import StrategyBrain
from app.brain.smart_router import SmartRouter
from app.brain.agent_reputation import AgentReputation
from app.brain.sector_brains import list_sector_brains, get_sector_brain
from app.core.envelopes import error, success
from app.core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/brain", tags=["brain"])


@router.get("/status")
async def brain_status(request: Request):
    """Return full cognitive architecture status."""
    cid = request.headers.get("x-correlation-id")
    try:
        macro = MacroBrain.get()
        status = macro.get_status()

        # Add reputation data
        rep = AgentReputation.get()
        status["reputation"]["rankings"] = rep.get_ranking(min_tasks=1)

        # Add routing stats
        smart = SmartRouter.get()
        status["smartRouter"]["routingHistory"] = smart.get_routing_history(limit=10)

        return success(status, cid)
    except Exception as exc:
        logger.error("brain_status_failed", error=str(exc))
        return JSONResponse(
            status_code=500,
            content=error("brain_error", str(exc), correlation_id=cid),
        )


@router.get("/sectors")
async def list_sectors(request: Request):
    """List all registered sector brains with metadata."""
    cid = request.headers.get("x-correlation-id")
    return success({
        "sectors": list_sector_brains(),
        "total": len(list_sector_brains()),
    }, cid)


@router.post("/process")
async def process_task(request: Request):
    """
    Process a task through the Macro Brain cognitive architecture.

    Body:
    {
        "task": "Build a REST API for user management",
        "context": "Optional context string",
        "taskType": "code" | "research" | "planning" | "general" | ...,
        "preferredMode": "fast" | "smart" | "deep" | "coding" | null,
        "sectorBrainId": "coding" | "research" | null (routes directly),
        "maxTokens": 2048,
        "stream": false
    }
    """
    cid = request.headers.get("x-correlation-id")

    try:
        body = await request.json()
    except Exception:
        return JSONResponse(
            status_code=400,
            content=error("invalid_request", "Invalid JSON body", correlation_id=cid),
        )

    task: str = (body.get("task") or "").strip()
    if not task:
        return JSONResponse(
            status_code=400,
            content=error("invalid_request", "task is required", correlation_id=cid),
        )

    context: str = body.get("context", "")
    task_type: str = body.get("taskType", "general")
    preferred_mode: str | None = body.get("preferredMode")
    sector_brain_id: str | None = body.get("sectorBrainId")
    max_tokens: int = min(int(body.get("maxTokens", 2048)), 4096)
    stream: bool = body.get("stream", False)

    macro = MacroBrain.get()

    if stream:
        return StreamingResponse(
            _stream_brain_process(macro, task, context, task_type, preferred_mode, sector_brain_id, max_tokens),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    result = await macro.process(
        task=task,
        context=context,
        task_type=task_type,
        preferred_mode=preferred_mode,
        sector_brain_id=sector_brain_id,
        max_tokens=max_tokens,
    )

    return success(result, cid)


async def _stream_brain_process(macro, task, context, task_type, preferred_mode, sector_brain_id, max_tokens):
    """Stream brain processing events via SSE."""
    try:
        routing = macro._smart_router.analyze_task(task=task, task_type=task_type, user_preferred_mode=preferred_mode)
        yield f"data: {json.dumps({'event': 'BRAIN_ROUTING', 'data': routing})}\n\n"
    except Exception as exc:
        yield f"data: {json.dumps({'event': 'BRAIN_ERROR', 'error': str(exc)})}\n\n"
        yield "data: [DONE]\n\n"
        return

    result = await macro.process(
        task=task, context=context, task_type=task_type,
        preferred_mode=preferred_mode, sector_brain_id=sector_brain_id,
        max_tokens=max_tokens,
    )

    yield f"data: {json.dumps({'event': 'BRAIN_RESULT', 'data': result})}\n\n"
    yield "data: [DONE]\n\n"


@router.post("/plan")
async def generate_plan(request: Request):
    """Generate a strategy plan (task graph) for a goal."""
    cid = request.headers.get("x-correlation-id")

    try:
        body = await request.json()
    except Exception:
        return JSONResponse(
            status_code=400,
            content=error("invalid_request", "Invalid JSON body", correlation_id=cid),
        )

    goal: str = (body.get("goal") or "").strip()
    if not goal:
        return JSONResponse(
            status_code=400,
            content=error("invalid_request", "goal is required", correlation_id=cid),
        )

    context: str = body.get("context", "")
    max_steps: int = min(int(body.get("maxSteps", 10)), 20)

    try:
        strategy = StrategyBrain.get()
        plan = await strategy.generate_plan(
            goal=goal,
            context=context,
            available_brains=list_sector_brains(),
            max_steps=max_steps,
        )
        return success(strategy.to_dict(plan), cid)
    except Exception as exc:
        logger.error("plan_generation_failed", error=str(exc))
        return JSONResponse(
            status_code=500,
            content=error("plan_error", str(exc), correlation_id=cid),
        )


@router.get("/reputation")
async def get_reputation(request: Request):
    """Get agent reputation rankings."""
    cid = request.headers.get("x-correlation-id")
    rep = AgentReputation.get()
    min_tasks = int(request.query_params.get("minTasks", 0))
    agent_type = request.query_params.get("agentType")

    return success({
        "rankings": rep.get_ranking(min_tasks=min_tasks, agent_type=agent_type),
        "totalTracked": len(rep.get_all_records()),
    }, cid)


@router.get("/routing")
async def get_routing_history(request: Request):
    """Get Smart Router history."""
    cid = request.headers.get("x-correlation-id")
    smart = SmartRouter.get()
    limit = int(request.query_params.get("limit", 20))
    return success({
        "routingHistory": smart.get_routing_history(limit=limit),
    }, cid)


@router.post("/sector/{sector_id}")
async def invoke_sector_brain(sector_id: str, request: Request):
    """Directly invoke a specific sector brain."""
    cid = request.headers.get("x-correlation-id")

    brain_class = get_sector_brain(sector_id)
    if brain_class is None:
        return JSONResponse(
            status_code=404,
            content=error("sector_not_found", f"No sector brain found for '{sector_id}'", correlation_id=cid),
        )

    try:
        body = await request.json()
    except Exception:
        body = {}

    task: str = (body.get("task") or "").strip()
    if not task:
        return JSONResponse(
            status_code=400,
            content=error("invalid_request", "task is required", correlation_id=cid),
        )

    context: str = body.get("context", "")
    max_tokens: int = min(int(body.get("maxTokens", 1024)), 4096)

    brain = brain_class()
    result = await brain.process(task=task, context=context, max_tokens=max_tokens)

    # Track reputation
    rep = AgentReputation.get()
    rep.record(
        agent_id=f"sector_{sector_id}",
        success=result.success,
        confidence=result.confidence,
        latency_ms=result.elapsed_ms,
        task_type=sector_id,
        agent_type="sector_brain",
    )

    return success({
        "sectorId": sector_id,
        "brainName": brain_class.BRAIN_NAME,
        "result": {
            "success": result.success,
            "output": result.output[:2000],
            "confidence": result.confidence,
            "reasoning": result.reasoning,
            "elapsedMs": result.elapsed_ms,
            "error": result.error,
        },
    }, cid)
