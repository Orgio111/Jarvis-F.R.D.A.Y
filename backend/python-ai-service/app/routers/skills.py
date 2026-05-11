"""Skills router — CRUD + execution for dynamic LLM-generated skills."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse

from app.core.envelopes import error, success
from app.core.logging import get_logger
from app.db.database import get_db
from app.services import skill_service

logger = get_logger(__name__)
router = APIRouter(prefix="/skills", tags=["skills"])


@router.get("")
async def list_skills(request: Request, db=Depends(get_db)) -> dict:
    cid = request.headers.get("x-correlation-id")
    skills = await skill_service.get_all(db)
    return success({"skills": skills, "total": len(skills)}, cid)


@router.post("")
async def create_skill(request: Request, db=Depends(get_db)) -> dict:
    cid = request.headers.get("x-correlation-id")
    try:
        body = await request.json()
    except Exception:
        return JSONResponse(status_code=400, content=error("invalid_request", "Invalid JSON", cid))

    name: str = body.get("name", "").strip()
    description: str = body.get("description", "").strip()
    if not name or not description:
        return JSONResponse(
            status_code=400,
            content=error("invalid_request", "name and description are required", cid),
        )

    try:
        skill = await skill_service.generate_and_store(
            db,
            name=name,
            description=description,
            task_context=body.get("taskContext", ""),
            category=body.get("category", "general"),
            origin="user",
        )
        return success(skill, cid)
    except Exception as exc:
        logger.error("skill_create_failed", error=str(exc))
        return JSONResponse(status_code=500, content=error("skill_error", str(exc), cid))


@router.get("/{skill_id}")
async def get_skill(skill_id: str, request: Request, db=Depends(get_db)) -> dict:
    cid = request.headers.get("x-correlation-id")
    skill = await skill_service.get_by_id(db, skill_id)
    if skill is None:
        return JSONResponse(status_code=404, content=error("not_found", f"Skill '{skill_id}' not found", cid))
    return success(skill, cid)


@router.patch("/{skill_id}")
async def update_skill(skill_id: str, request: Request, db=Depends(get_db)) -> dict:
    cid = request.headers.get("x-correlation-id")
    try:
        body = await request.json()
    except Exception:
        return JSONResponse(status_code=400, content=error("invalid_request", "Invalid JSON", cid))

    updated = await skill_service.update_skill(db, skill_id, body)
    if updated is None:
        return JSONResponse(status_code=404, content=error("not_found", f"Skill '{skill_id}' not found", cid))
    return success(updated, cid)


@router.delete("/{skill_id}")
async def delete_skill(skill_id: str, request: Request, db=Depends(get_db)) -> dict:
    cid = request.headers.get("x-correlation-id")
    deleted = await skill_service.delete_skill(db, skill_id)
    if not deleted:
        return JSONResponse(status_code=404, content=error("not_found", f"Skill '{skill_id}' not found", cid))
    return success({"deleted": True, "skillId": skill_id}, cid)


@router.post("/{skill_id}/execute")
async def execute_skill(skill_id: str, request: Request, db=Depends(get_db)) -> dict:
    cid = request.headers.get("x-correlation-id")
    try:
        body = await request.json()
    except Exception:
        body = {}

    params: dict = body.get("params", body)
    try:
        result = await skill_service.execute(db, skill_id, params)
        return success(result, cid)
    except Exception as exc:
        logger.error("skill_exec_router_error", skill_id=skill_id, error=str(exc))
        return JSONResponse(status_code=500, content=error("execution_error", str(exc), cid))
