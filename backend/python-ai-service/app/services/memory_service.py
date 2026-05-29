"""
Persistent Memory Service
─────────────────────────
Three complementary stores:

  1. SQLite (via SQLAlchemy)
     • Durable source of truth for every memory chunk
     • Survives restarts, stores metadata, importance, access counts

  2. Qdrant vector DB — 3-layer Letta-style memory
     • core      — pinned facts always injected into system prompt (~20 entries)
     • recall    — last 100 conversation turns, semantic search
     • archival  — full long-term history + crystallised skills
     • Replaces FAISS flat index (no real persistence, rebuilt from SQLite on restart)

  3. FAISS (legacy fallback)
     • Used only when Qdrant is unreachable
     • Rebuilt from SQLite on startup if Qdrant unavailable

Memory is typed:
  episodic   – conversation turns stored verbatim
  semantic   – synthesised facts / summaries
  procedural – how-to knowledge extracted from task completions

Every chat turn is auto-stored as episodic memory so the assistant has
full conversation history across sessions.
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.db.models import MemoryEntry
from app.memory.qdrant_memory import get_qdrant_memory, QdrantMemory

logger = get_logger(__name__)

# Optional dependency: NumPy is required for vector math / FAISS integration.
# If it's missing, the service should still start and health must remain 200.
try:
    import numpy as np  # type: ignore
    _NUMPY_AVAILABLE = True
except Exception as exc:  # noqa: BLE001
    np = None  # type: ignore[assignment]
    _NUMPY_AVAILABLE = False
    logger.warning("numpy_not_available_degraded_mode", error=str(exc))

_DATA_DIR = Path(os.getenv("DATA_DIR", "./data"))
_FAISS_DIR = _DATA_DIR / "faiss"
_FAISS_DIR.mkdir(parents=True, exist_ok=True)
_FAISS_INDEX_PATH = _FAISS_DIR / "memory.index"

_QDRANT_HOST = os.getenv("QDRANT_HOST", "qdrant")
_QDRANT_PORT = int(os.getenv("QDRANT_PORT", "6333"))

# Module-level singletons (warm once per process)
_embedder = None
_faiss_index = None
_index_map: list[int] = []  # maps FAISS row → SQLite id
_qdrant: QdrantMemory | None = None


# ─── Boot-time setup ──────────────────────────────────────────────────────────

async def boot(
    db: AsyncSession,
    embeddings_model: str = "sentence-transformers/all-MiniLM-L6-v2",
) -> None:
    """Called at service startup. Initialises Qdrant, then loads embedder + FAISS fallback."""
    global _embedder, _faiss_index, _index_map, _qdrant

    # ── 1. Qdrant (primary store) ─────────────────────────────────────────────
    try:
        _qdrant = get_qdrant_memory(host=_QDRANT_HOST, port=_QDRANT_PORT)
        logger.info("memory_qdrant_initialised", status=_qdrant.status())
    except Exception as exc:
        logger.warning("memory_qdrant_boot_failed", error=str(exc))
        _qdrant = None

    # ── 2. Embedder ───────────────────────────────────────────────────────────
    if not _NUMPY_AVAILABLE:
        logger.warning("memory_boot_numpy_missing", status="degraded")
        return

    try:
        from sentence_transformers import SentenceTransformer  # type: ignore
        _embedder = SentenceTransformer(embeddings_model)
        logger.info("memory_embedder_loaded", model=embeddings_model)
    except ImportError:
        logger.warning("sentence_transformers_not_installed", hint="pip install sentence-transformers")
        return

    # ── 3. FAISS (fallback only — skip if Qdrant is available) ───────────────
    if _qdrant is not None and _qdrant._available:
        logger.info("memory_faiss_skipped", reason="qdrant_available")
        return

    try:
        import faiss  # type: ignore
    except ImportError:
        logger.warning("faiss_not_installed", hint="pip install faiss-cpu")
        return

    if _FAISS_INDEX_PATH.exists():
        _faiss_index = faiss.read_index(str(_FAISS_INDEX_PATH))
        result = await db.execute(
            select(MemoryEntry.id).where(MemoryEntry.faiss_index.is_not(None))
            .order_by(MemoryEntry.faiss_index)
        )
        _index_map = [row[0] for row in result.fetchall()]
        logger.info("memory_faiss_loaded_fallback", vectors=_faiss_index.ntotal)
    else:
        result = await db.execute(select(MemoryEntry).order_by(MemoryEntry.id))
        entries = result.scalars().all()
        if entries:
            await _rebuild_index(entries)
        else:
            dim = _embedder.get_sentence_embedding_dimension()
            _faiss_index = faiss.IndexFlatIP(dim)
            _index_map = []
        logger.info("memory_faiss_created_fallback", vectors=len(_index_map))


# ─── Public API ───────────────────────────────────────────────────────────────

async def store(
    db: AsyncSession,
    content: str,
    metadata: dict[str, Any] | None = None,
    memory_type: str = "episodic",
    importance: float = 0.5,
) -> dict[str, Any]:
    """Persist a memory chunk to SQLite + Qdrant recall layer (or FAISS fallback)."""
    if metadata is None:
        metadata = {}

    entry = MemoryEntry(
        content=content,
        metadata_json=json.dumps(metadata),
        memory_type=memory_type,
        importance=importance,
        created_at=time.time(),
        last_accessed=time.time(),
    )
    db.add(entry)
    await db.flush()  # get the auto-increment id

    # ── Qdrant primary ────────────────────────────────────────────────────────
    if _qdrant is not None:
        qdrant_meta = {
            "db_id": entry.id,
            "memory_type": memory_type,
            "importance": importance,
            **metadata,
        }
        # High-importance semantic memories → also pin to core
        if memory_type == "semantic" and importance >= 0.8:
            _qdrant.upsert("core", content, qdrant_meta)
        else:
            _qdrant.upsert("recall", content, qdrant_meta)
    elif _embedder is not None and _faiss_index is not None:
        # ── FAISS fallback ────────────────────────────────────────────────────
        await _embed_and_add(db, entry)

    await db.commit()
    return {"id": entry.id, "stored": True, "type": memory_type}


async def store_core(
    db: AsyncSession,
    content: str,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Store a high-priority fact in the core memory layer (always in context)."""
    result = await store(db, content, metadata, memory_type="semantic", importance=1.0)
    if _qdrant is not None:
        _qdrant.promote_to_core(content, metadata or {})
    return {**result, "layer": "core"}


async def search(
    db: AsyncSession,
    query: str,
    top_k: int = 5,
    memory_type: str | None = None,
    layer: str = "recall",
) -> list[dict[str, Any]]:
    """
    Semantic nearest-neighbour search.

    Primary:  Qdrant (recall or archival layer)
    Fallback: FAISS flat index
    Degraded: SQLite LIKE
    """
    # ── Qdrant primary ────────────────────────────────────────────────────────
    if _qdrant is not None and _qdrant._available:
        meta_filter = {"memory_type": memory_type} if memory_type else None
        hits = _qdrant.search(layer, query, top_k=top_k, metadata_filter=meta_filter)
        results = []
        for h in hits:
            db_id = h.metadata.get("db_id")
            if db_id:
                row = await db.get(MemoryEntry, db_id)
                if row:
                    await db.execute(
                        update(MemoryEntry)
                        .where(MemoryEntry.id == db_id)
                        .values(last_accessed=time.time(), access_count=row.access_count + 1)
                    )
            results.append({
                "id": h.id,
                "content": h.content,
                "metadata": h.metadata,
                "type": h.metadata.get("memory_type", "episodic"),
                "importance": h.metadata.get("importance", 0.5),
                "score": h.score,
                "layer": h.layer,
            })
        await db.commit()
        return results

    # ── FAISS fallback ────────────────────────────────────────────────────────
    if (not _NUMPY_AVAILABLE) or _embedder is None or _faiss_index is None or _faiss_index.ntotal == 0:
        return await _fallback_search(db, query, top_k, memory_type)

    vec = _embedder.encode([query], normalize_embeddings=True).astype(np.float32)
    k = min(top_k * 2, _faiss_index.ntotal)
    distances, indices = _faiss_index.search(vec, k)

    results: list[dict[str, Any]] = []
    for dist, idx in zip(distances[0], indices[0]):
        if idx < 0 or idx >= len(_index_map):
            continue
        db_id = _index_map[idx]
        row = await db.get(MemoryEntry, db_id)
        if row is None:
            continue
        if memory_type and row.memory_type != memory_type:
            continue
        await db.execute(
            update(MemoryEntry)
            .where(MemoryEntry.id == db_id)
            .values(last_accessed=time.time(), access_count=row.access_count + 1)
        )
        results.append(_to_dict(row, score=float(dist)))
        if len(results) >= top_k:
            break

    await db.commit()
    return results


async def get_core_context() -> list[dict[str, Any]]:
    """Return all core memory entries for system prompt injection."""
    if _qdrant is not None:
        return _qdrant.get_core()
    return []


async def get_recent(
    db: AsyncSession,
    limit: int = 20,
    session_id: str | None = None,
) -> list[dict[str, Any]]:
    """Return the most recent episodic memories (optionally scoped to a session)."""
    q = select(MemoryEntry).where(MemoryEntry.memory_type == "episodic")
    if session_id:
        q = q.where(MemoryEntry.metadata_json.contains(session_id))
    q = q.order_by(MemoryEntry.created_at.desc()).limit(limit)
    result = await db.execute(q)
    return [_to_dict(e) for e in result.scalars().all()]


async def clear(db: AsyncSession, memory_type: str | None = None) -> dict[str, Any]:
    """Delete all (or a typed subset of) memory entries + wipe Qdrant / FAISS."""
    global _faiss_index, _index_map

    from sqlalchemy import delete as sql_delete

    q = sql_delete(MemoryEntry)
    if memory_type:
        q = q.where(MemoryEntry.memory_type == memory_type)
    result = await db.execute(q)
    await db.commit()

    # Wipe FAISS if active
    if _faiss_index is not None:
        _faiss_index.reset()
        _index_map = []
        if _FAISS_INDEX_PATH.exists():
            _FAISS_INDEX_PATH.unlink()

    # Note: Qdrant collections are not wiped on clear() — use Qdrant dashboard
    # or add an explicit admin endpoint if needed.

    return {"cleared": True, "rows_deleted": result.rowcount}


async def status(db: AsyncSession) -> dict[str, Any]:
    from sqlalchemy import func

    total_result = await db.execute(select(func.count(MemoryEntry.id)))
    total = total_result.scalar() or 0

    faiss_available = False
    try:
        import faiss  # type: ignore[import]  # noqa
        faiss_available = True
    except ImportError:
        pass

    qdrant_status = _qdrant.status() if _qdrant else {"available": False}

    return {
        "totalEntries": total,
        "qdrant": qdrant_status,
        "faissVectors": _faiss_index.ntotal if _faiss_index else 0,
        "faissAvailable": faiss_available,
        "embeddingsAvailable": _embedder is not None,
        "numpyAvailable": _NUMPY_AVAILABLE,
        "mode": (
            "qdrant" if (_qdrant and _qdrant._available)
            else "faiss" if _faiss_index
            else "degraded"
        ),
        "indexPath": str(_FAISS_INDEX_PATH),
    }


# ─── Internals ────────────────────────────────────────────────────────────────

async def _embed_and_add(db: AsyncSession, entry: MemoryEntry) -> None:
    """FAISS fallback: embed entry and add to in-process index."""
    if not _NUMPY_AVAILABLE or np is None:
        return

    import faiss  # type: ignore

    try:
        from app.routers.gpu import get_workload_router
        wr = get_workload_router()
    except Exception:
        wr = None

    async def _encode():
        return _embedder.encode([entry.content], normalize_embeddings=True).astype(np.float32)  # type: ignore[union-attr]

    if wr is not None:
        async with wr.acquire("embeddings"):
            vec = await _encode()
    else:
        vec = await _encode()

    if _faiss_index.ntotal == 0:  # type: ignore[union-attr]
        dim = vec.shape[1]
        globals()["_faiss_index"] = faiss.IndexFlatIP(dim)

    faiss_pos = _faiss_index.ntotal  # type: ignore[union-attr]
    _faiss_index.add(vec)  # type: ignore[union-attr]
    _index_map.append(entry.id)

    await db.execute(
        update(MemoryEntry)
        .where(MemoryEntry.id == entry.id)
        .values(faiss_index=faiss_pos)
    )
    faiss.write_index(_faiss_index, str(_FAISS_INDEX_PATH))


async def _rebuild_index(entries: list[MemoryEntry]) -> None:
    """FAISS fallback: rebuild in-process index from DB entries."""
    if not _NUMPY_AVAILABLE or np is None:
        return

    import faiss  # type: ignore

    global _faiss_index, _index_map

    texts = [e.content for e in entries]
    vecs = _embedder.encode(texts, normalize_embeddings=True).astype(np.float32)  # type: ignore[union-attr]
    dim = vecs.shape[1]
    _faiss_index = faiss.IndexFlatIP(dim)
    _faiss_index.add(vecs)
    _index_map = [e.id for e in entries]
    faiss.write_index(_faiss_index, str(_FAISS_INDEX_PATH))


async def _fallback_search(
    db: AsyncSession,
    query: str,
    top_k: int,
    memory_type: str | None,
) -> list[dict[str, Any]]:
    """SQLite LIKE search — last resort when neither Qdrant nor FAISS is available."""
    q = select(MemoryEntry)
    if memory_type:
        q = q.where(MemoryEntry.memory_type == memory_type)
    q = q.where(MemoryEntry.content.contains(query[:80]))
    q = q.order_by(MemoryEntry.importance.desc()).limit(top_k)
    result = await db.execute(q)
    return [_to_dict(e, score=0.0) for e in result.scalars().all()]


def _to_dict(entry: MemoryEntry, score: float = 1.0) -> dict[str, Any]:
    try:
        meta = json.loads(entry.metadata_json or "{}")
    except Exception:
        meta = {}
    return {
        "id": entry.id,
        "content": entry.content,
        "metadata": meta,
        "type": entry.memory_type,
        "importance": entry.importance,
        "score": round(score, 4),
        "createdAt": entry.created_at,
        "accessCount": entry.access_count,
    }
