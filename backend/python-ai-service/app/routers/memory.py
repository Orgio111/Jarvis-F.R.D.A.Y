from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.core.config import get_settings
from app.core.envelopes import error, success
from app.core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()


@router.get("/memory/status")
async def memory_status(request: Request) -> dict:
    correlation_id = request.headers.get("x-correlation-id")
    settings = get_settings()
    faiss_available = False
    embeddings_available = False
    try:
        import faiss  # type: ignore[import] # noqa: F401
        faiss_available = True
    except ImportError:
        pass
    try:
        import sentence_transformers  # type: ignore[import] # noqa: F401
        embeddings_available = True
    except ImportError:
        pass

    return success(
        {
            "enabled": settings.faiss_enabled,
            "faissAvailable": faiss_available,
            "embeddingsAvailable": embeddings_available,
            "indexPath": settings.faiss_index_path,
            "embeddingsModel": settings.embeddings_model,
        },
        correlation_id,
    )


@router.post("/memory/store")
async def memory_store(request: Request) -> dict:
    correlation_id = request.headers.get("x-correlation-id")
    settings = get_settings()

    if not settings.faiss_enabled:
        return JSONResponse(
            status_code=503,
            content=error("memory_disabled", "Memory (FAISS) is disabled", correlation_id=correlation_id),
        )

    try:
        body = await request.json()
    except Exception:
        return JSONResponse(
            status_code=400,
            content=error("invalid_request", "Request body must be valid JSON", correlation_id=correlation_id),
        )

    content: str = body.get("content", "").strip()
    metadata: dict = body.get("metadata", {})

    if not content:
        return JSONResponse(
            status_code=400,
            content=error("invalid_request", "content is required", correlation_id=correlation_id),
        )

    try:
        result = await _store_memory(content, metadata, settings)
        return success(result, correlation_id)
    except ImportError as exc:
        return JSONResponse(
            status_code=503,
            content=error(
                "memory_unavailable",
                f"Memory dependencies not installed: {exc}",
                correlation_id=correlation_id,
            ),
        )
    except Exception as exc:
        logger.error("memory_store_failed", error=str(exc))
        return JSONResponse(
            status_code=500,
            content=error("memory_error", str(exc), correlation_id=correlation_id),
        )


@router.post("/memory/search")
async def memory_search(request: Request) -> dict:
    correlation_id = request.headers.get("x-correlation-id")
    settings = get_settings()

    if not settings.faiss_enabled:
        return success({"results": [], "total": 0}, correlation_id)

    try:
        body = await request.json()
    except Exception:
        return JSONResponse(
            status_code=400,
            content=error("invalid_request", "Request body must be valid JSON", correlation_id=correlation_id),
        )

    query: str = body.get("query", "").strip()
    top_k: int = int(body.get("topK", 5))

    if not query:
        return JSONResponse(
            status_code=400,
            content=error("invalid_request", "query is required", correlation_id=correlation_id),
        )

    try:
        results = await _search_memory(query, top_k, settings)
        return success({"results": results, "total": len(results)}, correlation_id)
    except ImportError:
        return success({"results": [], "total": 0}, correlation_id)
    except Exception as exc:
        logger.error("memory_search_failed", error=str(exc))
        return success({"results": [], "total": 0}, correlation_id)


@router.delete("/memory/clear")
async def memory_clear(request: Request) -> dict:
    correlation_id = request.headers.get("x-correlation-id")
    return success({"cleared": True}, correlation_id)


# ─── Internal helpers ─────────────────────────────────────────────────────────

_index = None
_stored: list[dict] = []
_embedder = None


async def _get_embedder(settings):
    global _embedder
    if _embedder is None:
        from sentence_transformers import SentenceTransformer  # type: ignore[import]
        _embedder = SentenceTransformer(settings.embeddings_model)
    return _embedder


async def _store_memory(content: str, metadata: dict, settings) -> dict:
    import numpy as np
    import faiss  # type: ignore[import]
    global _index, _stored

    embedder = await _get_embedder(settings)
    vec = embedder.encode([content], normalize_embeddings=True)

    if _index is None:
        dim = vec.shape[1]
        _index = faiss.IndexFlatIP(dim)

    _index.add(vec.astype(np.float32))
    entry_id = len(_stored)
    _stored.append({"id": entry_id, "content": content, "metadata": metadata})
    return {"id": entry_id, "stored": True}


async def _search_memory(query: str, top_k: int, settings) -> list[dict]:
    import numpy as np
    global _index, _stored

    if _index is None or len(_stored) == 0:
        return []

    embedder = await _get_embedder(settings)
    vec = embedder.encode([query], normalize_embeddings=True)
    distances, indices = _index.search(vec.astype(np.float32), min(top_k, len(_stored)))

    results = []
    for dist, idx in zip(distances[0], indices[0]):
        if idx < 0:
            continue
        entry = _stored[idx].copy()
        entry["score"] = round(float(dist), 4)
        results.append(entry)
    return results
