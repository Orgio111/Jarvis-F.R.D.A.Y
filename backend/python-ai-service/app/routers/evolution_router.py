"""
Evolution & Pipeline Router — REST API for self-improvement systems.

Endpoints:
  GET    /evolution/status       — Evolution service status
  GET    /evolution/patterns     — Successful/failed execution patterns
  GET    /evolution/suggestions  — Optimization suggestions
  POST   /evolution/record       — Manually record an execution
  GET    /pipeline/status        — Autonomous pipeline status
  POST   /pipeline/run           — Run the autonomous pipeline
  GET    /pipeline/runs          — List recent pipeline runs
  GET    /pipeline/runs/{id}     — Get a specific pipeline run
  GET    /self-improvement/loop  — Self-improvement loop status
  POST   /self-improvement/loop/evaluate — Evaluate and improve a result
"""
from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.core.envelopes import error, success
from app.core.logging import get_logger
from app.services.evolution_service import EvolutionService
from app.services.autonomous_pipeline import AutonomousPipeline
from app.services.self_improvement_loop import SelfImprovementLoop

logger = get_logger(__name__)
router = APIRouter(tags=["evolution"])


# ─── Evolution ────────────────────────────────────────────────────────────────

@router.get("/evolution/status")
async def evolution_status(request: Request):
    cid = request.headers.get("x-correlation-id")
    try:
        evo = EvolutionService.get()
        return success(evo.get_status(), cid)
    except Exception as exc:
        return JSONResponse(status_code=500, content=error("evolution_error", str(exc), correlation_id=cid))


@router.get("/evolution/patterns")
async def evolution_patterns(request: Request):
    cid = request.headers.get("x-correlation-id")
    try:
        evo = EvolutionService.get()
        return success(evo.get_all(), cid)
    except Exception as exc:
        return JSONResponse(status_code=500, content=error("evolution_error", str(exc), correlation_id=cid))


@router.get("/evolution/suggestions")
async def evolution_suggestions(request: Request):
    cid = request.headers.get("x-correlation-id")
    try:
        evo = EvolutionService.get()
        return success({"suggestions": evo.get_optimization_suggestions()}, cid)
    except Exception as exc:
        return JSONResponse(status_code=500, content=error("evolution_error", str(exc), correlation_id=cid))


@router.post("/evolution/record")
async def evolution_record(request: Request):
    cid = request.headers.get("x-correlation-id")
    try:
        body = await request.json()
    except Exception:
        return JSONResponse(
            status_code=400,
            content=error("invalid_request", "Invalid JSON body", correlation_id=cid),
        )

    evo = EvolutionService.get()
    record_id = evo.record_execution(
        task=body.get("task", ""),
        task_type=body.get("taskType", "general"),
        success=body.get("success", False),
        output=body.get("output", ""),
        model_used=body.get("modelUsed", ""),
        confidence=body.get("confidence", 0.0),
        latency_ms=body.get("latencyMs", 0.0),
        error=body.get("error"),
        metadata=body.get("metadata"),
    )
    return success({"recordId": record_id, "stored": True}, cid)


# ─── Self-Improvement Loop ────────────────────────────────────────────────────

@router.get("/self-improvement/loop")
async def improvement_loop_status(request: Request):
    cid = request.headers.get("x-correlation-id")
    try:
        loop = SelfImprovementLoop.get()
        return success({
            "status": loop.get_status(),
            "history": loop.get_history(limit=10),
        }, cid)
    except Exception as exc:
        return JSONResponse(status_code=500, content=error("improvement_error", str(exc), correlation_id=cid))


@router.post("/self-improvement/loop/evaluate")
async def improvement_evaluate(request: Request):
    cid = request.headers.get("x-correlation-id")
    try:
        body = await request.json()
    except Exception:
        return JSONResponse(
            status_code=400,
            content=error("invalid_request", "Invalid JSON body", correlation_id=cid),
        )

    task: str = (body.get("task") or "").strip()
    task_type: str = body.get("taskType", "general")
    context: str = body.get("context", "")
    result: dict = body.get("result", {})

    if not task:
        return JSONResponse(
            status_code=400,
            content=error("invalid_request", "task is required", correlation_id=cid),
        )

    loop = SelfImprovementLoop.get()
    improved = await loop.evaluate_and_improve(
        task=task,
        task_type=task_type,
        initial_result=result,
        context=context,
    )
    return success(improved, cid)


# ─── Autonomous Pipeline ──────────────────────────────────────────────────────

@router.get("/pipeline/status")
async def pipeline_status(request: Request):
    cid = request.headers.get("x-correlation-id")
    try:
        pipeline = AutonomousPipeline.get()
        return success(pipeline.get_status(), cid)
    except Exception as exc:
        return JSONResponse(status_code=500, content=error("pipeline_error", str(exc), correlation_id=cid))


@router.post("/pipeline/run")
async def pipeline_run(request: Request):
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

    pipeline = AutonomousPipeline.get()
    result = await pipeline.run(
        goal=goal,
        context=body.get("context", ""),
        task_type=body.get("taskType", "general"),
        max_retries=min(int(body.get("maxRetries", 2)), 5),
        auto_fix=body.get("autoFix", True),
    )
    return success(result, cid)


@router.get("/pipeline/runs")
async def pipeline_runs(request: Request):
    cid = request.headers.get("x-correlation-id")
    limit = int(request.query_params.get("limit", 10))
    pipeline = AutonomousPipeline.get()
    return success({"runs": pipeline.get_runs(limit=limit)}, cid)


@router.get("/pipeline/runs/{run_id}")
async def pipeline_run_detail(run_id: str, request: Request):
    cid = request.headers.get("x-correlation-id")
    pipeline = AutonomousPipeline.get()
    run = pipeline.get_run(run_id)
    if run is None:
        return JSONResponse(
            status_code=404,
            content=error("not_found", f"Run '{run_id}' not found", correlation_id=cid),
        )
    return success(run, cid)
