"""API routes for the Swarm Manager — distributed agent swarm orchestration."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException

from app.core.envelopes import success_response, error_response
from app.services.swarm_manager_service import SwarmManagerService

router = APIRouter(prefix="/swarm", tags=["swarm"])


def _get_service() -> SwarmManagerService:
    try:
        return SwarmManagerService.get()
    except RuntimeError:
        raise HTTPException(status_code=503, detail="SwarmManagerService not initialized")


@router.get("/status")
async def get_swarm_status() -> dict[str, Any]:
    """Get overall swarm system status."""
    svc = _get_service()
    return success_response(svc.get_status())


@router.get("/swarms")
async def list_swarms() -> dict[str, Any]:
    """List all active swarms."""
    svc = _get_service()
    return success_response({"swarms": svc.list_swarms()})


@router.get("/swarms/{swarm_id}")
async def get_swarm(swarm_id: str) -> dict[str, Any]:
    """Get detailed info about a specific swarm."""
    svc = _get_service()
    swarm = svc.get_swarm(swarm_id)
    if not swarm:
        return error_response(f"Swarm {swarm_id} not found", status_code=404)
    return success_response(swarm)


@router.post("/swarms")
async def create_swarm(role: str, min_agents: int = 1, max_agents: int = 3) -> dict[str, Any]:
    """Spawn a new swarm with the given role."""
    svc = _get_service()
    result = svc.spawn_swarm(role, min_agents, max_agents)
    if not result.get("success"):
        return error_response(result.get("error", "Failed to spawn swarm"), status_code=400)
    return success_response(result)


@router.delete("/swarms/{swarm_id}")
async def delete_swarm(swarm_id: str) -> dict[str, Any]:
    """Terminate a swarm."""
    svc = _get_service()
    success = svc.terminate_swarm(swarm_id)
    if not success:
        return error_response(f"Swarm {swarm_id} not found", status_code=404)
    return success_response({"terminated": True, "swarmId": swarm_id})


@router.get("/health")
async def swarm_health() -> dict[str, Any]:
    """Health check all swarms."""
    svc = _get_service()
    return success_response({"health": svc.health_check_all()})


@router.post("/auto-scale")
async def auto_scale() -> dict[str, Any]:
    """Trigger auto-scaling on all swarms."""
    svc = _get_service()
    results = svc.auto_scale_all()
    return success_response({"scalingActions": results})


@router.post("/heal")
async def heal_swarms() -> dict[str, Any]:
    """Self-heal all degraded swarms."""
    svc = _get_service()
    results = svc.heal_all()
    return success_response({"healingActions": results})


@router.get("/route")
async def route_task(task: str, task_type: str = "general") -> dict[str, Any]:
    """Route a task to the best-fit swarm."""
    svc = _get_service()
    result = svc.route_brain_task(task, task_type)
    return success_response(result)
