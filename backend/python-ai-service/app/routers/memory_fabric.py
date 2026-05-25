"""API routes for the Memory Fabric — multi-layered cognitive memory."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query

from fastapi.responses import JSONResponse

from app.core.envelopes import success, error

router = APIRouter(prefix="/memory-fabric", tags=["memory-fabric"])


def _get_service():
    try:
        from app.services.memory_fabric_service import MemoryFabricService
        return MemoryFabricService.get()
    except RuntimeError:
        raise HTTPException(status_code=503, detail="MemoryFabricService not initialized")


@router.get("/status")
async def get_status() -> dict[str, Any]:
    """Get memory fabric status."""
    svc = _get_service()
    return success(svc.get_status())


@router.post("/store")
async def store_memory(
    content: str,
    layer: str = "episodic",
    tags: str = "",
    source: str = "",
    importance: float = 0.5,
    confidence: float = 0.8,
) -> dict[str, Any]:
    """Store a new memory entry."""
    svc = _get_service()
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


@router.get("/entries/{entry_id}")
async def get_memory(entry_id: str) -> dict[str, Any]:
    """Get a specific memory entry by ID."""
    svc = _get_service()
    entry = svc.get(entry_id)
    if not entry:
        return JSONResponse(status_code=404, content=error("not_found", f"Entry {entry_id} not found"))
    return success(entry)


@router.get("/search")
async def search_memory(
    q: str = Query(..., description="Search query"),
    layer: str | None = Query(None, description="Filter by layer"),
    limit: int = Query(20, ge=1, le=100),
) -> dict[str, Any]:
    """Search memory by text content."""
    svc = _get_service()
    results = svc.search(q, layer=layer, limit=limit)
    return success({"results": results, "count": len(results)})


@router.get("/query")
async def query_memory(
    text: str = "",
    layers: str = "episodic,semantic,procedural",
    tags: str = "",
    min_importance: float = 0.0,
    limit: int = 20,
    source: str | None = None,
) -> dict[str, Any]:
    """Query memory with multiple filters."""
    svc = _get_service()
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


@router.get("/cross-layer")
async def cross_layer_query(
    topic: str = Query(..., description="Topic to search across all layers"),
    per_layer: int = Query(5, ge=1, le=20),
) -> dict[str, Any]:
    """Query all memory layers for a topic."""
    svc = _get_service()
    results = svc.cross_layer_query(topic, limit_per_layer=per_layer)
    return success(results)


@router.get("/recent")
async def recent_memories(
    layer: str | None = None,
    limit: int = Query(10, ge=1, le=50),
) -> dict[str, Any]:
    """Get recent memory entries."""
    svc = _get_service()
    results = svc.get_recent(layer=layer, limit=limit)
    return success({"results": results})


@router.post("/prune")
async def prune_memory() -> dict[str, Any]:
    """Prune stale/low-importance entries."""
    svc = _get_service()
    result = svc.prune()
    return success(result)


@router.get("/stats")
async def memory_stats() -> dict[str, Any]:
    """Get memory fabric statistics."""
    svc = _get_service()
    return success_response(svc.stats())
