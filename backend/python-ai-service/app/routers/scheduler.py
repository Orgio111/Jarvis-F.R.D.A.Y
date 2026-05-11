"""Scheduler router — manage cron/interval/one-shot background tasks via REST."""
from __future__ import annotations

from uuid import uuid4

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.core.envelopes import error, success
from app.core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/scheduler", tags=["scheduler"])

_VALID_TRIGGER_TYPES = {"cron", "interval", "date"}
_VALID_ACTION_TYPES = {"chat_prompt", "skill_call", "http_request"}


def _get_worker():
    from app.scheduler.worker import SchedulerWorker
    return SchedulerWorker.get()


@router.get("/tasks")
async def list_tasks(request: Request) -> dict:
    cid = request.headers.get("x-correlation-id")
    tasks = await _get_worker().list_tasks()
    return success({"tasks": tasks, "total": len(tasks)}, cid)


@router.post("/tasks")
async def create_task(request: Request) -> dict:
    cid = request.headers.get("x-correlation-id")
    try:
        body = await request.json()
    except Exception:
        return JSONResponse(status_code=400, content=error("invalid_request", "Invalid JSON", cid))

    name: str = body.get("name", "").strip()
    trigger_type: str = body.get("triggerType", "").strip()
    trigger_config: dict = body.get("triggerConfig", {})
    action: dict = body.get("action", {})

    if not name:
        return JSONResponse(status_code=400, content=error("invalid_request", "name is required", cid))
    if trigger_type not in _VALID_TRIGGER_TYPES:
        return JSONResponse(
            status_code=400,
            content=error("invalid_request", f"triggerType must be one of {_VALID_TRIGGER_TYPES}", cid),
        )
    if action.get("type") not in _VALID_ACTION_TYPES:
        return JSONResponse(
            status_code=400,
            content=error("invalid_request", f"action.type must be one of {_VALID_ACTION_TYPES}", cid),
        )

    task_id = f"task_{uuid4().hex[:10]}"
    try:
        task = await _get_worker().add_task({
            "task_id": task_id,
            "name": name,
            "description": body.get("description", ""),
            "trigger_type": trigger_type,
            "trigger_config": trigger_config,
            "action": action,
            "enabled": body.get("enabled", True),
        })
        return success(task, cid)
    except Exception as exc:
        logger.error("scheduler_create_failed", error=str(exc))
        return JSONResponse(status_code=500, content=error("scheduler_error", str(exc), cid))


@router.delete("/tasks/{task_id}")
async def delete_task(task_id: str, request: Request) -> dict:
    cid = request.headers.get("x-correlation-id")
    removed = await _get_worker().remove_task(task_id)
    if not removed:
        return JSONResponse(status_code=404, content=error("not_found", f"Task '{task_id}' not found", cid))
    return success({"deleted": True, "taskId": task_id}, cid)


@router.post("/tasks/{task_id}/pause")
async def pause_task(task_id: str, request: Request) -> dict:
    cid = request.headers.get("x-correlation-id")
    await _get_worker().pause_task(task_id)
    return success({"paused": True, "taskId": task_id}, cid)


@router.post("/tasks/{task_id}/resume")
async def resume_task(task_id: str, request: Request) -> dict:
    cid = request.headers.get("x-correlation-id")
    await _get_worker().resume_task(task_id)
    return success({"resumed": True, "taskId": task_id}, cid)


@router.get("/status")
async def scheduler_status(request: Request) -> dict:
    cid = request.headers.get("x-correlation-id")
    tasks = await _get_worker().list_tasks()
    enabled = sum(1 for t in tasks if t["enabled"])
    return success(
        {
            "schedulerRunning": True,
            "totalTasks": len(tasks),
            "enabledTasks": enabled,
        },
        cid,
    )
