"""User profile router — get, patch, and summarise the dynamic user model."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse

from app.core.envelopes import error, success
from app.core.logging import get_logger
from app.db.database import get_db
from app.services import profile_service

logger = get_logger(__name__)
router = APIRouter(prefix="/profile", tags=["profile"])


@router.get("")
async def get_profile(request: Request, db=Depends(get_db)) -> dict:
    cid = request.headers.get("x-correlation-id")
    user_id = request.headers.get("x-user-id", "default")
    profile = await profile_service.get_or_create(db, user_id)
    return success(profile, cid)


@router.patch("")
async def patch_profile(request: Request, db=Depends(get_db)) -> dict:
    cid = request.headers.get("x-correlation-id")
    user_id = request.headers.get("x-user-id", "default")
    try:
        patches = await request.json()
    except Exception:
        return JSONResponse(status_code=400, content=error("invalid_request", "Invalid JSON", cid))

    updated = await profile_service.patch(db, patches, user_id)
    return success(updated, cid)


@router.get("/summary")
async def profile_summary(request: Request, db=Depends(get_db)) -> dict:
    """Returns a compact text summary suitable for injecting into a system prompt."""
    cid = request.headers.get("x-correlation-id")
    user_id = request.headers.get("x-user-id", "default")
    summary = await profile_service.context_summary(db, user_id)
    return success({"summary": summary}, cid)


@router.delete("")
async def reset_profile(request: Request, db=Depends(get_db)) -> dict:
    """Reset the user profile to defaults."""
    cid = request.headers.get("x-correlation-id")
    user_id = request.headers.get("x-user-id", "default")
    from sqlalchemy import delete
    from app.db.models import UserProfile
    await db.execute(delete(UserProfile).where(UserProfile.user_id == user_id))
    await db.commit()
    return success({"reset": True, "userId": user_id}, cid)
