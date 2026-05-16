"""
Persistent Memory Service
─────────────────────────
Two complementary stores:

  1. SQLite (via SQLAlchemy)
     • Durable source of truth for every memory chunk
     • Survives restarts, stores metadata, importance, access counts

  2. FAISS flat-IP index (file-persisted to DATA_DIR/faiss/)
     • Fast semantic nearest-neighbour search
     • Rebuilt from SQLite on startup if the index file is missing

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

import numpy as np
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.db.models import MemoryEntry

logger = get_logger(__name__)

_DATA_DIR = Path(os.getenv("DATA_DIR", "./data"))
_FAISS_DIR = _DATA_DIR / "faiss"
_FAISS_DIR.mkdir(parents=True, exist_ok=True)
_FAISS_INDEX_PATH = _FAISS_DIR / "memory.index"

# Module-level singletons (warm once per process)
_embedder = None
_faiss_index = None
_index_map: list[int] = []  # maps FAISS row → SQLite id


# ─── Boot-time setup ──────────────────────────────────────────────────────────

async def boot(db: AsyncSession, embeddings_model: str = "sentence-transformers/all-MiniLM-L6-v2") -> None:
    """Called at service startup. Loads embedder + rebuilds FAISS if needed."""
    global _embedder, _faiss_index, _index_map

    try:
        from sentence_transformers import SentenceTransformer  # type: ignore
        _embedder = SentenceTransformer(embeddings_model)
        logger.info("memory_embedder_loaded", model=embeddings_model)
    except ImportError:
        logger.warning("sentence_transformers_not_installed", hint="pip install sentence-transformers")
        return

    import faiss  # type: ignore

    if _FAISS_INDEX_PATH.exists():
        _faiss_index = faiss.read_index(str(_FAISS_INDEX_PATH))
        # Rebuild the map from DB order
        result = await db.execute(
            select(MemoryEntry.id).where(MemoryEntry.faiss_index.is_not(None))
            .order_by(MemoryEntry.faiss_index)
        )
        _index_map = [row[0] for row in result.fetchall()]
        logger.info("memory_faiss_loaded", vectors=_faiss_index.ntotal)
    else:
        # Bootstrap from existing DB entries
        result = await db.execute(select(MemoryEntry).order_by(MemoryEntry.id))
        entries = result.scalars().all()
        if entries:
            await _rebuild_index(entries)
        else:
            dim = _embedder.get_sentence_embedding_dimension()
            _faiss_index = faiss.IndexFlatIP(dim)
            _index_map = []
        logger.info("memory_faiss_created", vectors=len(_index_map))


# ─── Public API ───────────────────────────────────────────────────────────────

async def store(
    db: AsyncSession,
    content: str,
    metadata: dict[str, Any] | None = None,
    memory_type: str = "episodic",
    importance: float = 0.5,
) -> dict[str, Any]:
    """Persist a memory chunk to SQLite + embed into FAISS."""
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

    if _embedder is not None and _faiss_index is not None:
        await _embed_and_add(db, entry)

    await db.commit()
    return {"id": entry.id, "stored": True, "type": memory_type}


async def search(
    db: AsyncSession,
    query: str,
    top_k: int = 5,
    memory_type: str | None = None,
) -> list[dict[str, Any]]:
    """Semantic nearest-neighbour search. Falls back to SQLite LIKE if no FAISS."""
    if _embedder is None or _faiss_index is None or _faiss_index.ntotal == 0:
        return await _fallback_search(db, query, top_k, memory_type)

    import faiss  # type: ignore

    vec = _embedder.encode([query], normalize_embeddings=True).astype(np.float32)
    k = min(top_k * 2, _faiss_index.ntotal)  # fetch extra to allow filtering
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
        # Update access tracking
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
    """Delete all (or a typed subset of) memory entries + rebuild FAISS."""
    global _faiss_index, _index_map

    from sqlalchemy import delete as sql_delete

    q = sql_delete(MemoryEntry)
    if memory_type:
        q = q.where(MemoryEntry.memory_type == memory_type)
    result = await db.execute(q)
    await db.commit()

    # Wipe FAISS
    if _faiss_index is not None:
        _faiss_index.reset()
        _index_map = []
        if _FAISS_INDEX_PATH.exists():
            _FAISS_INDEX_PATH.unlink()

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

    embeddings_available = _embedder is not None

    return {
        "totalEntries": total,
        "faissVectors": _faiss_index.ntotal if _faiss_index else 0,
        "faissAvailable": faiss_available,
        "embeddingsAvailable": embeddings_available,
        "indexPath": str(_FAISS_INDEX_PATH),
    }


# ─── Internals ────────────────────────────────────────────────────────────────

async def _embed_and_add(db: AsyncSession, entry: MemoryEntry) -> None:
    import faiss  # type: ignore

    vec = _embedder.encode([entry.content], normalize_embeddings=True).astype(np.float32)  # type: ignore[union-attr]

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
    # Persist index to disk
    faiss.write_index(_faiss_index, str(_FAISS_INDEX_PATH))


async def _rebuild_index(entries: list[MemoryEntry]) -> None:
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
