"""
Skill Marketplace Router
──────────────────────────
App-store style endpoints for the Jarvis Skill OS.

GET  /marketplace/skills            — list all (search/filter/sort)
GET  /marketplace/skills/{id}       — detail + version chain
GET  /marketplace/trending          — top by trust_score * usage
GET  /marketplace/search            — semantic + keyword search
POST /marketplace/install           — install by skill_id or GitHub URL
POST /marketplace/uninstall/{id}    — soft disable
POST /marketplace/rate/{id}         — submit 1-5 star rating
POST /marketplace/publish/{id}      — publish skill to shared registry
POST /marketplace/github/import     — import directly from GitHub URL
GET  /marketplace/github/status     — check if git is available
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse

from app.core.envelopes import error, success
from app.core.logging import get_logger
from app.db.database import get_db
from app.services import skill_registry, skill_evolution
from app.services import skill_service

logger = get_logger(__name__)
router = APIRouter(prefix="/marketplace", tags=["marketplace"])


# ─── Listing / Search ────────────────────────────────────────────────────────

@router.get("/stats")
async def marketplace_stats(request: Request, db=Depends(get_db)) -> dict:
    """Aggregate stats across the skill registry."""
    from sqlalchemy import select, func
    from app.db.models import Skill as SkillModel

    cid = request.headers.get("x-correlation-id")
    total = (await db.execute(select(func.count()).select_from(SkillModel))).scalar_one()
    enabled = (await db.execute(
        select(func.count()).select_from(SkillModel).where(SkillModel.enabled.is_(True))
    )).scalar_one()
    total_exec = (await db.execute(select(func.sum(SkillModel.execution_count)))).scalar_one() or 0
    avg_trust_row = (await db.execute(
        select(func.avg(SkillModel.trust_score)).select_from(SkillModel)
    )).scalar_one()
    avg_trust = round(float(avg_trust_row or 0), 3)

    # Per-category counts
    cat_rows = (await db.execute(
        select(SkillModel.category, func.count()).group_by(SkillModel.category)
    )).all()
    categories = {row[0]: row[1] for row in cat_rows}

    return success({
        "totalSkills": total,
        "enabledSkills": enabled,
        "totalExecutions": int(total_exec),
        "avgTrustScore": avg_trust,
        "categories": categories,
    }, cid)


@router.get("/skills")
async def list_marketplace_skills(
    request: Request,
    category: str | None = None,
    limit: int = 50,
    db=Depends(get_db),
) -> dict:
    cid = request.headers.get("x-correlation-id")
    skills = await skill_registry.rank_skills(db, category=category, limit=limit)
    return success({"skills": skills, "total": len(skills)}, cid)


@router.get("/skills/{skill_id}")
async def get_marketplace_skill(
    skill_id: str,
    request: Request,
    db=Depends(get_db),
) -> dict:
    cid = request.headers.get("x-correlation-id")
    skill = await skill_service.get_by_id(db, skill_id)
    if skill is None:
        return JSONResponse(
            status_code=404,
            content=error("not_found", f"Skill '{skill_id}' not found", cid),
        )
    # Also fetch version chain
    chain = await skill_evolution.get_version_chain(db, skill_id)
    return success({"skill": skill, "version_chain": chain}, cid)


@router.get("/trending")
async def trending(
    request: Request,
    limit: int = 20,
    db=Depends(get_db),
) -> dict:
    cid = request.headers.get("x-correlation-id")
    skills = await skill_registry.trending_skills(db, limit=limit)
    return success({"skills": skills, "total": len(skills)}, cid)


@router.get("/search")
async def search(
    request: Request,
    q: str = "",
    tags: str = "",  # comma-separated
    category: str | None = None,
    limit: int = 30,
    db=Depends(get_db),
) -> dict:
    cid = request.headers.get("x-correlation-id")
    tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else []
    skills = await skill_registry.search_skills(
        db, query=q, tags=tag_list, category=category, limit=limit
    )
    return success({"skills": skills, "query": q, "tags": tag_list, "total": len(skills)}, cid)


# ─── Install / Uninstall ─────────────────────────────────────────────────────

@router.post("/install")
async def install_skill(request: Request, db=Depends(get_db)) -> dict:
    """
    Install a skill by:
      - { "skill_id": "..." }         → enable existing disabled skill
      - { "github_url": "..." }       → import from GitHub
      - { "name": ..., "description": ... } → generate new skill via LLM
    """
    cid = request.headers.get("x-correlation-id")
    try:
        body = await request.json()
    except Exception:
        return JSONResponse(status_code=400, content=error("invalid_request", "Invalid JSON", cid))

    # Case 1: enable existing skill
    if "skill_id" in body:
        skill_id = body["skill_id"]
        updated = await skill_service.update_skill(db, skill_id, {"enabled": True})
        if updated is None:
            return JSONResponse(status_code=404, content=error("not_found", f"Skill '{skill_id}' not found", cid))
        return success({"installed": True, "skill": updated}, cid)

    # Case 2: GitHub import
    if "github_url" in body:
        url = body["github_url"].strip()
        if not url:
            return JSONResponse(status_code=400, content=error("invalid_request", "github_url is required", cid))
        try:
            from app.services.github_importer import import_from_github
            skill = await import_from_github(
                db=db,
                url=url,
                publisher=body.get("publisher", "github_import"),
                category=body.get("category", "imported"),
            )
            return success({"installed": True, "skill": skill, "source": "github"}, cid)
        except Exception as exc:
            logger.error("github_import_failed", url=url, error=str(exc))
            return JSONResponse(status_code=500, content=error("import_error", str(exc), cid))

    # Case 3: Generate new skill via LLM
    name = body.get("name", "").strip()
    description = body.get("description", "").strip()
    if not name or not description:
        return JSONResponse(
            status_code=400,
            content=error("invalid_request", "Provide skill_id, github_url, or name+description", cid),
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
        return success({"installed": True, "skill": skill, "source": "generated"}, cid)
    except Exception as exc:
        logger.error("skill_install_generate_failed", error=str(exc))
        return JSONResponse(status_code=500, content=error("install_error", str(exc), cid))


@router.post("/uninstall/{skill_id}")
async def uninstall_skill(skill_id: str, request: Request, db=Depends(get_db)) -> dict:
    """Soft uninstall — disables the skill (preserves history)."""
    cid = request.headers.get("x-correlation-id")
    updated = await skill_service.update_skill(db, skill_id, {"enabled": False})
    if updated is None:
        return JSONResponse(status_code=404, content=error("not_found", f"Skill '{skill_id}' not found", cid))
    return success({"uninstalled": True, "skill_id": skill_id}, cid)


# ─── Rating ──────────────────────────────────────────────────────────────────

@router.post("/rate/{skill_id}")
async def rate_skill(skill_id: str, request: Request, db=Depends(get_db)) -> dict:
    """Submit a 1-5 star rating. Updates trust_score."""
    cid = request.headers.get("x-correlation-id")
    try:
        body = await request.json()
    except Exception:
        return JSONResponse(status_code=400, content=error("invalid_request", "Invalid JSON", cid))

    rating = body.get("rating")
    if rating is None or not isinstance(rating, (int, float)) or not (1 <= rating <= 5):
        return JSONResponse(
            status_code=400,
            content=error("invalid_request", "rating must be a number 1-5", cid),
        )

    result = await skill_registry.submit_rating(db, skill_id, float(rating))
    if result is None:
        return JSONResponse(status_code=404, content=error("not_found", f"Skill '{skill_id}' not found", cid))
    return success(result, cid)


# ─── Publish ─────────────────────────────────────────────────────────────────

@router.post("/publish/{skill_id}")
async def publish_skill(skill_id: str, request: Request, db=Depends(get_db)) -> dict:
    """Mark skill as published to shared marketplace."""
    cid = request.headers.get("x-correlation-id")
    try:
        body = await request.json()
    except Exception:
        body = {}

    patch: dict = {"published": True}
    if "publisher" in body:
        patch["publisher"] = body["publisher"]

    updated = await skill_service.update_skill(db, skill_id, patch)
    if updated is None:
        return JSONResponse(status_code=404, content=error("not_found", f"Skill '{skill_id}' not found", cid))
    return success({"published": True, "skill": updated}, cid)


# ─── GitHub Import ───────────────────────────────────────────────────────────

@router.post("/github/import")
async def github_import(request: Request, db=Depends(get_db)) -> dict:
    """Direct GitHub import endpoint."""
    cid = request.headers.get("x-correlation-id")
    try:
        body = await request.json()
    except Exception:
        return JSONResponse(status_code=400, content=error("invalid_request", "Invalid JSON", cid))

    url = body.get("url", "").strip()
    if not url:
        return JSONResponse(status_code=400, content=error("invalid_request", "url is required", cid))

    try:
        from app.services.github_importer import import_from_github
        skill = await import_from_github(
            db=db,
            url=url,
            publisher=body.get("publisher", "github_import"),
            category=body.get("category", "imported"),
        )
        return success({"skill": skill, "source": "github", "url": url}, cid)
    except Exception as exc:
        logger.error("github_import_router_failed", url=url, error=str(exc))
        return JSONResponse(status_code=500, content=error("import_error", str(exc), cid))


@router.get("/github/status")
async def github_status(request: Request) -> dict:
    """Check if git is available in the sandbox."""
    cid = request.headers.get("x-correlation-id")
    import subprocess
    try:
        result = subprocess.run(["git", "--version"], capture_output=True, text=True, timeout=5)
        return success({
            "git_available": result.returncode == 0,
            "git_version": result.stdout.strip(),
        }, cid)
    except Exception as exc:
        return success({"git_available": False, "error": str(exc)}, cid)


# ─── Evolution endpoints ──────────────────────────────────────────────────────

@router.post("/evolve/run")
async def run_evolution(request: Request, db=Depends(get_db)) -> dict:
    """Manually trigger a skill evolution cycle."""
    cid = request.headers.get("x-correlation-id")
    result = await skill_evolution.run_evolution_cycle(db)
    return success(result, cid)


@router.post("/evolve/{skill_id}")
async def evolve_skill(skill_id: str, request: Request, db=Depends(get_db)) -> dict:
    """Force-evolve a specific skill."""
    cid = request.headers.get("x-correlation-id")
    try:
        body = await request.json()
    except Exception:
        body = {}

    from sqlalchemy import select
    from app.db.models import Skill
    result_q = await db.execute(select(Skill).where(Skill.skill_id == skill_id))
    skill = result_q.scalar_one_or_none()
    if skill is None:
        return JSONResponse(status_code=404, content=error("not_found", f"Skill '{skill_id}' not found", cid))

    try:
        new_skill = await skill_evolution.patch_skill(db, skill, body.get("error_context", ""))
        return success({"evolved": True, "new_skill": new_skill}, cid)
    except Exception as exc:
        logger.error("manual_evolve_failed", skill_id=skill_id, error=str(exc))
        return JSONResponse(status_code=500, content=error("evolve_error", str(exc), cid))


@router.get("/evolve/{skill_id}/history")
async def skill_version_history(skill_id: str, request: Request, db=Depends(get_db)) -> dict:
    """Get full version chain for a skill."""
    cid = request.headers.get("x-correlation-id")
    chain = await skill_evolution.get_version_chain(db, skill_id)
    return success({"skill_id": skill_id, "version_chain": chain, "versions": len(chain)}, cid)
