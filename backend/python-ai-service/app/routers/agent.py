"""Agent router — triggers the plan→act→reflect→improve loop, streamed via SSE."""
from __future__ import annotations

import json

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse, StreamingResponse

from app.core.envelopes import error, success
from app.core.logging import get_logger
from app.db.database import get_db
from app.services import agent_service, skill_service

logger = get_logger(__name__)
router = APIRouter(prefix="/agent", tags=["agent"])


@router.post("/run")
async def run_agent(request: Request, db=Depends(get_db)):
    """
    Run the full agentic loop for a given goal.
    Streams SSE events: AGENT_START, AGENT_PLANNING, AGENT_PLAN_READY,
    AGENT_STEP_START, AGENT_STEP_DONE, AGENT_REFLECTING, AGENT_REFLECTION, AGENT_DONE.
    """
    cid = request.headers.get("x-correlation-id", "")
    user_id = request.headers.get("x-user-id", "default")

    try:
        body = await request.json()
    except Exception:
        return JSONResponse(status_code=400, content=error("invalid_request", "Invalid JSON", cid))

    goal: str = body.get("goal", "").strip()
    if not goal:
        return JSONResponse(
            status_code=400,
            content=error("invalid_request", "goal is required", cid),
        )

    context: str = body.get("context", "")
    stream: bool = body.get("stream", True)
    max_iterations: int = min(int(body.get("maxIterations", 3)), 5)

    # Fetch available skills to give to the planner
    available_skills = await skill_service.get_all(db, enabled_only=True)

    if stream:
        return StreamingResponse(
            _sse_loop(db, goal, context, available_skills, user_id, max_iterations),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    # Non-streaming: collect all events and return the DONE event
    result_event: dict = {}
    async for event in agent_service.run_task(db, goal, context, available_skills, user_id, max_iterations):
        if event.get("event") == "AGENT_DONE":
            result_event = event
    return success(result_event, cid)


async def _sse_loop(db, goal, context, skills, user_id, max_iterations):
    async for event in agent_service.run_task(db, goal, context, skills, user_id, max_iterations):
        yield f"data: {json.dumps(event)}\n\n"
    yield "data: [DONE]\n\n"


@router.get("/status")
async def agent_status(request: Request) -> dict:
    cid = request.headers.get("x-correlation-id")
    return success(
        {
            "agentEnabled": True,
            "maxIterations": 5,
            "maxStepsPerPlan": 10,
            "autoSkillCreation": True,
        },
        cid,
    )
