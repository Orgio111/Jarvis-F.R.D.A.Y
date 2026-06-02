"""
Memory router — delegates to the persistent MemoryService (SQLite + FAISS).
Also includes Memory Fabric (multi-layered cognitive memory) routes.
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import JSONResponse

from app.core.envelopes import error, success
from app.core.logging import get_logger
from app.db.database import get_db
from app.services import memory_service

logger = get_logger(__name__)

# ─── Router: Memory (SQLite + FAISS) ──────────────────────────────────────────

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


# ═══════════════════════════════════════════════════════════════════════════════
# Memory Fabric (multi-layered cognitive memory — merged from memory_fabric.py)
# ═══════════════════════════════════════════════════════════════════════════════

memory_fabric_router = APIRouter(prefix="/memory-fabric", tags=["memory-fabric"])


def _get_fabric_service():
    try:
        from app.services.memory_fabric_service import MemoryFabricService
        return MemoryFabricService.get()
    except RuntimeError:
        raise HTTPException(status_code=503, detail="MemoryFabricService not initialized")


@memory_fabric_router.get("/status")
async def mf_get_status() -> dict[str, Any]:
    """Get memory fabric status."""
    svc = _get_fabric_service()
    return success(await svc.get_status())


@memory_fabric_router.post("/store")
async def mf_store_memory(
    content: str,
    layer: str = "episodic",
    tags: str = "",
    source: str = "",
    importance: float = 0.5,
    confidence: float = 0.8,
) -> dict[str, Any]:
    """Store a new memory entry."""
    svc = _get_fabric_service()
    tag_list = [t.strip() for t in tags.split(",")] if tags else []
    result = svc.store(
        content=content,
        layer=layer,
        tags=tag_list,
        source=source,
        importance=importance,
        confidence=confidence,
    )
    return success(result)


@memory_fabric_router.get("/entries/{entry_id}")
async def mf_get_memory(entry_id: str) -> dict[str, Any]:
    """Get a specific memory entry by ID."""
    svc = _get_fabric_service()
    entry = svc.get_entry(entry_id)
    if not entry:
        return JSONResponse(status_code=404, content=error("not_found", f"Entry {entry_id} not found"))
    return success(entry)


@memory_fabric_router.get("/search")
async def mf_search_memory(
    q: str = Query(..., description="Search query"),
    layer: str | None = Query(None, description="Filter by layer"),
    limit: int = Query(20, ge=1, le=100),
) -> dict[str, Any]:
    """Search memory by text content."""
    svc = _get_fabric_service()
    results = await svc.search(q, layer=layer, limit=limit)
    return success({"results": results, "count": len(results)})


@memory_fabric_router.get("/query")
async def mf_query_memory(
    text: str = "",
    layers: str = "episodic,semantic,procedural",
    tags: str = "",
    min_importance: float = 0.0,
    limit: int = 20,
    source: str | None = None,
) -> dict[str, Any]:
    """Query memory with multiple filters."""
    svc = _get_fabric_service()
    layer_list = [l.strip() for l in layers.split(",")] if layers else None
    tag_list = [t.strip() for t in tags.split(",")] if tags else []
    results = svc.query(
        text=text,
        layers=layer_list,
        tags=tag_list,
        min_importance=min_importance,
        limit=limit,
        source=source,
    )
    return success({"results": results, "count": len(results)})


@memory_fabric_router.get("/cross-layer")
async def mf_cross_layer_query(
    topic: str = Query(..., description="Topic to search across all layers"),
    per_layer: int = Query(5, ge=1, le=20),
) -> dict[str, Any]:
    """Query all memory layers for a topic."""
    svc = _get_fabric_service()
    results = svc.cross_layer_query(topic, limit_per_layer=per_layer)
    return success(results)


@memory_fabric_router.get("/recent")
async def mf_recent_memories(
    layer: str | None = None,
    limit: int = Query(10, ge=1, le=50),
) -> dict[str, Any]:
    """Get recent memory entries."""
    svc = _get_fabric_service()
    results = svc.get_recent(layer=layer, limit=limit)
    return success({"results": results})


@memory_fabric_router.post("/prune")
async def mf_prune_memory() -> dict[str, Any]:
    """Prune stale/low-importance entries."""
    svc = _get_fabric_service()
    result = svc.prune()
    return success(result)


@memory_fabric_router.get("/stats")
async def mf_memory_stats() -> dict[str, Any]:
    """Get memory fabric statistics."""
    svc = _get_fabric_service()
    return success(svc.stats())
