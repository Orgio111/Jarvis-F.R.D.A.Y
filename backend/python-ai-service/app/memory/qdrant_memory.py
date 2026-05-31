"""
QdrantMemory — 3-layer persistent memory backed by Qdrant vector DB.

Layers:
  core      — always-in-context facts, pinned to system prompt (~20 entries, ~2K tokens)
  recall    — recent conversation turns, last 100, semantic search enabled
  archival  — full long-term history + crystallised skills, semantic search enabled

Falls back to a no-op in-memory dict if Qdrant is unreachable (service still boots).
"""
from __future__ import annotations

import json
import logging
import time
import uuid
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

_COLLECTIONS = {
    "core":     "jarvis_core",
    "recall":   "jarvis_recall",
    "archival": "jarvis_archival",
}

_RECALL_LIMIT = 100          # max entries in recall layer before oldest → archival
_VECTOR_DIM   = 384          # sentence-transformers/all-MiniLM-L6-v2 output dim
_CORE_TOKEN_BUDGET = 2000    # approximate token budget for core layer content


@dataclass
class MemoryHit:
    id: str
    content: str
    metadata: dict[str, Any]
    score: float
    layer: str


class QdrantMemory:
    """
    Thin wrapper around qdrant-client providing the 3-layer memory interface.

    Usage:
        qm = QdrantMemory(host="qdrant", port=6333)
        qm.ensure_collections()   # call once at boot
        qm.upsert("recall", "User asked about Python", {"session": "abc"})
        hits = qm.search("recall", "programming language question", top_k=5)
        core_entries = qm.get_core()
    """

    def __init__(self, host: str = "localhost", port: int = 6333):
        self._host = host
        self._port = port
        self._client = None
        self._available = False
        self._fallback: dict[str, list[dict]] = {"core": [], "recall": [], "archival": []}
        self._embedder = None
        self._connect()

    # ─── Connection ───────────────────────────────────────────────────────────

    def _connect(self) -> None:
        try:
            from qdrant_client import QdrantClient  # type: ignore
            self._client = QdrantClient(host=self._host, port=self._port, timeout=5)
            # Verify connectivity
            self._client.get_collections()
            self._available = True
            logger.info("qdrant_connected", extra={"host": self._host, "port": self._port})
        except Exception as exc:
            logger.warning(
                "qdrant_unavailable_fallback_mode",
                extra={"error": str(exc), "host": self._host},
            )
            self._available = False

    def ensure_collections(self) -> None:
        """Create collections if they don't exist. Safe to call multiple times."""
        if not self._available:
            return
        try:
            from qdrant_client.models import Distance, VectorParams  # type: ignore
            existing = {c.name for c in self._client.get_collections().collections}
            for layer, cname in _COLLECTIONS.items():
                if cname not in existing:
                    self._client.create_collection(
                        collection_name=cname,
                        vectors_config=VectorParams(size=_VECTOR_DIM, distance=Distance.COSINE),
                    )
                    logger.info("qdrant_collection_created", extra={"collection": cname})
        except Exception as exc:
            logger.warning("qdrant_ensure_collections_failed", extra={"error": str(exc)})

    # ─── Embedder ─────────────────────────────────────────────────────────────

    def _get_embedder(self):
        if self._embedder is not None:
            return self._embedder
        try:
            from sentence_transformers import SentenceTransformer  # type: ignore
            self._embedder = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
        except Exception as exc:
            logger.warning("qdrant_embedder_unavailable", extra={"error": str(exc)})
        return self._embedder

    def _embed(self, text: str) -> list[float] | None:
        embedder = self._get_embedder()
        if embedder is None:
            return None
        try:
            import numpy as np  # type: ignore
            vec = embedder.encode([text], normalize_embeddings=True)
            return vec[0].tolist()
        except Exception as exc:
            logger.warning("qdrant_embed_failed", extra={"error": str(exc)})
            return None

    # ─── Core public API ──────────────────────────────────────────────────────

    def upsert(
        self,
        layer: str,
        content: str,
        metadata: dict[str, Any] | None = None,
        entry_id: str | None = None,
    ) -> str:
        """Embed and store content in the given layer. Returns the entry ID."""
        if metadata is None:
            metadata = {}
        entry_id = entry_id or str(uuid.uuid4())
        payload = {
            "content": content,
            "created_at": time.time(),
            **metadata,
        }

        if not self._available:
            # Fallback: in-memory list
            self._fallback[layer].append({"id": entry_id, **payload})
            return entry_id

        vec = self._embed(content)
        if vec is None:
            # Can't embed — store with zero vector (searchable by metadata only)
            vec = [0.0] * _VECTOR_DIM

        try:
            from qdrant_client.models import PointStruct  # type: ignore
            cname = _COLLECTIONS[layer]
            self._client.upsert(
                collection_name=cname,
                points=[PointStruct(id=entry_id, vector=vec, payload=payload)],
            )
            # Enforce recall limit after insert
            if layer == "recall":
                self._evict_oldest_recall()
        except Exception as exc:
            logger.warning("qdrant_upsert_failed", extra={"layer": layer, "error": str(exc)})

        return entry_id

    def search(
        self,
        layer: str,
        query: str,
        top_k: int = 5,
        metadata_filter: dict[str, Any] | None = None,
    ) -> list[MemoryHit]:
        """Semantic nearest-neighbour search in a layer."""
        if not self._available:
            return self._fallback_search(layer, query, top_k)

        vec = self._embed(query)
        if vec is None:
            return []

        try:
            from qdrant_client.models import Filter, FieldCondition, MatchValue  # type: ignore
            cname = _COLLECTIONS[layer]
            qdrant_filter = None
            if metadata_filter:
                conditions = [
                    FieldCondition(key=k, match=MatchValue(value=v))
                    for k, v in metadata_filter.items()
                ]
                qdrant_filter = Filter(must=conditions)

            # qdrant-client >= 1.10 uses query_points() instead of search()
            result = self._client.query_points(
                collection_name=cname,
                query=vec,
                limit=top_k,
                query_filter=qdrant_filter,
                with_payload=True,
            )
            hits = result.points
            return [
                MemoryHit(
                    id=str(h.id),
                    content=h.payload.get("content", ""),
                    metadata={k: v for k, v in h.payload.items() if k != "content"},
                    score=round(h.score, 4),
                    layer=layer,
                )
                for h in hits
            ]
        except Exception as exc:
            logger.warning("qdrant_search_failed", extra={"layer": layer, "error": str(exc)})
            return []

    def get_core(self) -> list[dict[str, Any]]:
        """Return all core memory entries (for system prompt injection)."""
        if not self._available:
            return self._fallback.get("core", [])

        try:
            cname = _COLLECTIONS["core"]
            result = self._client.scroll(
                collection_name=cname,
                limit=50,
                with_payload=True,
                with_vectors=False,
            )
            entries = []
            token_count = 0
            for point in result[0]:
                content = point.payload.get("content", "")
                # Rough token estimate: 1 token ≈ 4 chars
                token_count += len(content) // 4
                if token_count > _CORE_TOKEN_BUDGET:
                    break
                entries.append({
                    "id": str(point.id),
                    "content": content,
                    "metadata": {k: v for k, v in point.payload.items() if k != "content"},
                })
            return entries
        except Exception as exc:
            logger.warning("qdrant_get_core_failed", extra={"error": str(exc)})
            return []

    def promote_to_core(self, content: str, metadata: dict[str, Any] | None = None) -> str:
        """Store an entry in the core layer (persistent user facts/preferences)."""
        return self.upsert("core", content, metadata or {})

    def promote(self, entry_id: str, from_layer: str, to_layer: str) -> bool:
        """Move an entry from one layer to another."""
        if not self._available:
            return False
        try:
            from_cname = _COLLECTIONS[from_layer]
            result = self._client.retrieve(
                collection_name=from_cname,
                ids=[entry_id],
                with_payload=True,
                with_vectors=True,
            )
            if not result:
                return False
            point = result[0]
            to_cname = _COLLECTIONS[to_layer]
            from qdrant_client.models import PointStruct  # type: ignore
            self._client.upsert(
                collection_name=to_cname,
                points=[PointStruct(
                    id=point.id,
                    vector=point.vector,
                    payload=point.payload,
                )],
            )
            self._client.delete(
                collection_name=from_cname,
                points_selector=[entry_id],
            )
            return True
        except Exception as exc:
            logger.warning("qdrant_promote_failed", extra={"error": str(exc)})
            return False

    def delete(self, layer: str, entry_id: str) -> bool:
        """Delete a specific entry from a layer."""
        if not self._available:
            return False
        try:
            cname = _COLLECTIONS[layer]
            self._client.delete(collection_name=cname, points_selector=[entry_id])
            return True
        except Exception as exc:
            logger.warning("qdrant_delete_failed", extra={"error": str(exc)})
            return False

    def count(self, layer: str) -> int:
        """Return number of entries in a layer."""
        if not self._available:
            return len(self._fallback.get(layer, []))
        try:
            cname = _COLLECTIONS[layer]
            return self._client.count(collection_name=cname).count
        except Exception:
            return 0

    def status(self) -> dict[str, Any]:
        return {
            "available": self._available,
            "host": self._host,
            "port": self._port,
            "collections": {
                layer: self.count(layer) for layer in _COLLECTIONS
            },
        }

    # ─── Internals ────────────────────────────────────────────────────────────

    def _evict_oldest_recall(self) -> None:
        """If recall > limit, move oldest entry to archival."""
        try:
            count = self.count("recall")
            if count <= _RECALL_LIMIT:
                return
            # Scroll oldest by created_at
            cname = _COLLECTIONS["recall"]
            from qdrant_client.models import OrderBy  # type: ignore
            result = self._client.scroll(
                collection_name=cname,
                limit=count - _RECALL_LIMIT,
                with_payload=True,
                with_vectors=True,
                order_by=OrderBy(key="created_at", direction="asc"),
            )
            for point in result[0]:
                # Move to archival
                archival_cname = _COLLECTIONS["archival"]
                from qdrant_client.models import PointStruct  # type: ignore
                self._client.upsert(
                    collection_name=archival_cname,
                    points=[PointStruct(
                        id=point.id,
                        vector=point.vector,
                        payload={**point.payload, "evicted_from": "recall"},
                    )],
                )
                self._client.delete(collection_name=cname, points_selector=[str(point.id)])
        except Exception as exc:
            # OrderBy may not be available in older qdrant-client versions — skip silently
            logger.debug("qdrant_evict_recall_skipped", extra={"error": str(exc)})

    def _fallback_search(self, layer: str, query: str, top_k: int) -> list[MemoryHit]:
        """Simple substring search over in-memory fallback store."""
        query_lower = query.lower()
        entries = self._fallback.get(layer, [])
        matches = [
            e for e in entries
            if query_lower in e.get("content", "").lower()
        ]
        return [
            MemoryHit(
                id=m["id"],
                content=m.get("content", ""),
                metadata={k: v for k, v in m.items() if k not in ("id", "content")},
                score=0.5,
                layer=layer,
            )
            for m in matches[:top_k]
        ]


# ─── Module-level singleton ───────────────────────────────────────────────────

_instance: QdrantMemory | None = None


def get_qdrant_memory(host: str = "qdrant", port: int = 6333) -> QdrantMemory:
    """Return or create the process-level QdrantMemory singleton."""
    global _instance
    if _instance is None:
        _instance = QdrantMemory(host=host, port=port)
        _instance.ensure_collections()
    return _instance
