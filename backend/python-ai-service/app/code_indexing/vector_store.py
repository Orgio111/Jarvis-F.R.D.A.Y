"""
Vector store for code chunk embeddings.

Wraps FAISS (flat-IP index) for fast semantic nearest-neighbour search.
Persists to disk and supports incremental addition / full rebuild.

Based on the existing memory_service.py FAISS pattern.
"""

from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Any

import numpy as np

from app.code_indexing.chunker import CodeChunk
from app.code_indexing.embedder import embed_chunks, embed_query, embed_dimension
from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)

# Module-level globals
_index = None          # faiss.Index
_chunks: list[CodeChunk] = []   # chunk metadata, index-aligned
_index_dir: Path | None = None
_dirty = False         # whether the index needs persisting


# ─── Initialisation ───────────────────────────────────────────────────────────


async def init_index(force_rebuild: bool = False) -> bool:
    """Initialize or load the FAISS code index."""
    global _index, _chunks, _index_dir, _dirty

    settings = get_settings()
    data_dir = Path(settings.data_dir or "./data")
    _index_dir = data_dir / "code_index"
    _index_dir.mkdir(parents=True, exist_ok=True)

    index_path = _index_dir / "code_index.faiss"
    meta_path = _index_dir / "code_meta.npy"

    try:
        import faiss
    except ImportError:
        logger.warning("faiss_not_installed_code_index", hint="pip install faiss-cpu")
        return False

    if not force_rebuild and index_path.exists() and meta_path.exists():
        try:
            _index = faiss.read_index(str(index_path))
            # Load chunk metadata
            meta_data = np.load(str(meta_path), allow_pickle=True)
            _chunks = list(meta_data) if meta_data.ndim == 1 else [meta_data]
            logger.info("code_index_loaded", vectors=_index.ntotal, chunks=len(_chunks))
            _dirty = False
            return True
        except Exception as exc:
            logger.warning("code_index_load_failed_rebuilding", error=str(exc))

    # Create fresh index
    dim = embed_dimension()
    if dim <= 0:
        dim = 384  # fallback
    _index = faiss.IndexFlatIP(dim)
    _chunks = []
    _dirty = False
    logger.info("code_index_created", dim=dim)
    return True


# ─── Public API ───────────────────────────────────────────────────────────────


async def add_chunks(chunks: list[CodeChunk]) -> int:
    """Add chunks to the index. Returns number added."""
    global _index, _chunks, _dirty

    if _index is None:
        ok = await init_index()
        if not ok:
            return 0

    if not chunks:
        return 0

    # Prepare texts for embedding
    texts = [_prep_chunk_text(c) for c in chunks]
    vecs = await embed_chunks(texts)

    if vecs is None or vecs.shape[0] == 0:
        return 0

    # Ensure dimension match
    if vecs.shape[1] != _index.d:
        logger.warning("dimension_mismatch",
                       expected=_index.d, got=vecs.shape[1])
        return 0

    _index.add(vecs)
    _chunks.extend(chunks)
    _dirty = True

    # Persist after every add (for safety; can be batched later)
    await persist()

    return len(chunks)


async def search(
    query: str,
    top_k: int = 10,
    language: str | None = None,
    chunk_type: str | None = None,
) -> list[dict[str, Any]]:
    """Semantic search over indexed code chunks."""
    if _index is None or _index.ntotal == 0:
        return []

    query_vec = await embed_query(query)
    if query_vec is None:
        return []

    k = min(top_k * 3, _index.ntotal)
    distances, indices = _index.search(query_vec, k)

    results: list[dict[str, Any]] = []
    for dist, idx in zip(distances[0], indices[0]):
        if idx < 0 or idx >= len(_chunks):
            continue

        chunk = _chunks[idx]
        if language and chunk.language != language:
            continue
        if chunk_type and chunk.chunk_type != chunk_type:
            continue

        results.append({
            "chunkId": chunk.id,
            "filePath": chunk.file_path,
            "language": chunk.language,
            "startLine": chunk.start_line,
            "endLine": chunk.end_line,
            "signature": chunk.signature,
            "chunkType": chunk.chunk_type,
            "score": float(dist),
            "content": chunk.content[:2000],  # limit content length
            "imports": chunk.imports[:5],
            "symbols": chunk.symbols[:5],
        })

        if len(results) >= top_k:
            break

    return results


async def search_by_symbol(symbol: str, language: str | None = None) -> list[dict[str, Any]]:
    """Search for chunks containing a specific symbol name."""
    results: list[dict[str, Any]] = []
    for chunk in _chunks:
        if any(symbol in s for s in chunk.symbols):
            if language and chunk.language != language:
                continue
            results.append({
                "chunkId": chunk.id,
                "filePath": chunk.file_path,
                "language": chunk.language,
                "startLine": chunk.start_line,
                "endLine": chunk.end_line,
                "signature": chunk.signature,
                "chunkType": chunk.chunk_type,
                "score": 1.0,
                "content": chunk.content[:2000],
                "symbols": chunk.symbols[:5],
            })
    return results


async def search_by_file(file_path: str) -> list[dict[str, Any]]:
    """Get all chunks for a specific file."""
    results: list[dict[str, Any]] = []
    for chunk in _chunks:
        if chunk.file_path == file_path:
            results.append({
                "chunkId": chunk.id,
                "filePath": chunk.file_path,
                "language": chunk.language,
                "startLine": chunk.start_line,
                "endLine": chunk.end_line,
                "signature": chunk.signature,
                "chunkType": chunk.chunk_type,
                "content": chunk.content[:2000],
                "score": 1.0,
                "symbols": chunk.symbols[:5],
            })
    return results


def status() -> dict[str, Any]:
    """Return index status information."""
    ntotal = _index.ntotal if _index is not None else 0
    return {
        "vectorCount": ntotal,
        "chunksCount": len(_chunks),
        "dimension": _index.d if _index is not None else 0,
        "dirty": _dirty,
        "indexPath": str(_index_dir / "code_index.faiss") if _index_dir else None,
        "isLoaded": _index is not None,
    }


async def clear() -> None:
    """Wipe the index."""
    global _index, _chunks, _dirty
    if _index is not None:
        _index.reset()
    _chunks = []
    _dirty = True
    await persist()
    logger.info("code_index_cleared")


async def persist() -> None:
    """Persist the index to disk."""
    global _dirty
    if _index is None or _index_dir is None or not _dirty:
        return

    import faiss

    index_path = _index_dir / "code_index.faiss"
    meta_path = _index_dir / "code_meta.npy"

    try:
        faiss.write_index(_index, str(index_path))
        np.save(str(meta_path), np.array(_chunks, dtype=object))
        _dirty = False
        logger.debug("code_index_persisted", vectors=_index.ntotal)
    except Exception as exc:
        logger.warning("code_index_persist_failed", error=str(exc))


# ─── Helpers ──────────────────────────────────────────────────────────────────


def _prep_chunk_text(chunk: CodeChunk) -> str:
    """Prepare chunk text for embedding — includes context."""
    parts = [
        f"File: {chunk.file_path}",
        f"Language: {chunk.language}",
        f"Type: {chunk.chunk_type}",
        f"Signature: {chunk.signature}",
        f"Symbols: {', '.join(chunk.symbols[:5])}" if chunk.symbols else "",
        "",
        chunk.content[:1500],  # limit context length
    ]
    return "\n".join(parts)
