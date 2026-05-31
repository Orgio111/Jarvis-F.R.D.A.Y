"""
Session Replay API router.

GET  /replay/sessions              — list sessions
POST /replay/sessions              — create session
GET  /replay/sessions/{id}         — get full session with events
POST /replay/sessions/{id}/events  — append event
POST /replay/sessions/{id}/close   — close session
DELETE /replay/sessions/{id}       — delete session
"""
from __future__ import annotations

import time
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.core.envelopes import success, error
from app.session_replay.store import SessionReplayStore
from app.session_replay.models import ReplayEvent, EventKind

router = APIRouter(prefix="/replay", tags=["session_replay"])


# ── schemas ───────────────────────────────────────────────────────────────────

class CreateSessionRequest(BaseModel):
    title: str = "Untitled Session"
    session_type: str = "chat"
    tags: list[str] = []
    metadata: dict[str, Any] = {}


class AppendEventRequest(BaseModel):
    kind: str
    data: dict[str, Any] = {}
    model_used: str | None = None
    duration_ms: float = 0.0
    timestamp: float | None = None


# ── endpoints ─────────────────────────────────────────────────────────────────

@router.get("/sessions")
async def list_sessions(
    limit: int = 50,
    offset: int = 0,
    session_type: str | None = None,
    tag: str | None = None,
):
    store = SessionReplayStore.get()
    sessions = store.list_sessions(
        limit=limit, offset=offset,
        session_type=session_type, tag=tag,
    )
    return success({"sessions": sessions, "count": len(sessions)})


@router.post("/sessions")
async def create_session(body: CreateSessionRequest):
    store = SessionReplayStore.get()
    sess = store.create_session(
        title=body.title,
        session_type=body.session_type,
        tags=body.tags,
        metadata=body.metadata,
    )
    return success(sess.to_dict(include_events=False))


@router.get("/sessions/{session_id}")
async def get_session(session_id: str):
    store = SessionReplayStore.get()
    sess = store.get_session(session_id)
    if not sess:
        raise HTTPException(status_code=404, detail="Session not found")
    return success(sess.to_dict(include_events=True))


@router.post("/sessions/{session_id}/events")
async def append_event(session_id: str, body: AppendEventRequest):
    store = SessionReplayStore.get()
    try:
        kind = EventKind(body.kind)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Unknown event kind: {body.kind}")

    event = ReplayEvent(
        kind=kind,
        data=body.data,
        model_used=body.model_used,
        duration_ms=body.duration_ms,
        timestamp=body.timestamp or time.time(),
    )
    ok = store.append_event(session_id, event)
    if not ok:
        raise HTTPException(status_code=404, detail="Session not found")
    return success({"event_id": event.event_id})


@router.post("/sessions/{session_id}/close")
async def close_session(session_id: str):
    store = SessionReplayStore.get()
    ok = store.close_session(session_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Session not found")
    return success({"closed": True})


@router.delete("/sessions/{session_id}")
async def delete_session(session_id: str):
    store = SessionReplayStore.get()
    store.delete_session(session_id)
    return success({"deleted": True})
