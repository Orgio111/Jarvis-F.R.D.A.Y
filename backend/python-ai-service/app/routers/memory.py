"""
Memory router — delegates to the persistent MemoryService (SQLite + FAISS).
Replaces the previous in-process volatile implementation so all memories
survive container restarts when the data volume is mounted.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse

from app.core.envelopes import error, success
from app.core.logging import get_logger
from app.db.database import get_db
from app.services import memory_service

logger = get_logger(__name__)
router = APIRouter()


@router.get("/memory/status")
async def memory_status(request: Request, db=Depends(get_db)) -> dict:
    cid = request.headers.get("x-correlation-id")
    return success(await memory_service.status(db), cid)


@router.post("/memory/store")
async def memory_store(request: Request, db=Depends(get_db)) -> dict:
    cid = request.headers.get("x-correlation-id")
    try:
        body = await request.json()
    except Exception:
        return JSONResponse(status_code=400, content=error("invalid_request", "Invalid JSON", cid))

    content: str = body.get("content", "").strip()
    if not content:
        return JSONResponse(status_code=400, content=error("invalid_request", "content is required", cid))

    try:
        result = await memory_service.store(
            db,
            content=content,
            metadata=body.get("metadata", {}),
            memory_type=body.get("type", "episodic"),
            importance=float(body.get("importance", 0.5)),
        )
        return success(result, cid)
    except Exception as exc:
        logger.error("memory_store_failed", error=str(exc))
        return JSONResponse(status_code=500, content=error("memory_error", str(exc), cid))


@router.post("/memory/search")
async def memory_search(request: Request, db=Depends(get_db)) -> dict:
    cid = request.headers.get("x-correlation-id")
    try:
        body = await request.json()
    except Exception:
        return JSONResponse(status_code=400, content=error("invalid_request", "Invalid JSON", cid))

    query: str = body.get("query", "").strip()
    if not query:
        return JSONResponse(status_code=400, content=error("invalid_request", "query is required", cid))

    results = await memory_service.search(
        db,
        query=query,
        top_k=int(body.get("topK", 5)),
        memory_type=body.get("type"),
    )
    return success({"results": results, "total": len(results)}, cid)


@router.get("/memory/recent")
async def memory_recent(request: Request, db=Depends(get_db)) -> dict:
    cid = request.headers.get("x-correlation-id")
    session_id = request.headers.get("x-session-id")
    limit = int(request.query_params.get("limit", "20"))
    entries = await memory_service.get_recent(db, limit=limit, session_id=session_id)
    return success({"entries": entries, "total": len(entries)}, cid)


@router.delete("/memory/clear")
async def memory_clear(request: Request, db=Depends(get_db)) -> dict:
    cid = request.headers.get("x-correlation-id")
    memory_type = request.query_params.get("type")
    result = await memory_service.clear(db, memory_type=memory_type)
    return success(result, cid)
