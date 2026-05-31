"""
Memory Fabric Service — multi-layered cognitive memory for the JARVIS backend.

Integrates the Memory Fabric package with the existing memory system:
  - Wraps MemoryFabric singleton
  - Provides API-friendly methods for store/query/search
  - Connects to FAISS for embedding-based semantic search
  - Auto-prunes stale entries
"""

from __future__ import annotations

import time
from typing import Any

from app.core.config import Settings
from app.core.logging import get_logger

# Optional import — the memory-fabric package may not be installed
try:
    from memory_fabric.fabric import (
        FabricConfig,
        MemoryFabric,
        MemoryLayer,
        MemoryQuery,
    )
    _MEMORY_FABRIC_AVAILABLE = True
except ImportError:
    FabricConfig = None  # type: ignore
    MemoryFabric = None  # type: ignore
    MemoryLayer = None  # type: ignore
    MemoryQuery = None  # type: ignore
    _MEMORY_FABRIC_AVAILABLE = False

logger = get_logger(__name__)


class MemoryFabricService:
    """
    Wraps MemoryFabric for the JARVIS backend.

    Provides three cognitive memory layers:
      - EPISODIC: conversations, executions, workflow traces
      - SEMANTIC: concepts, knowledge, architecture understanding
      - PROCEDURAL: successful patterns, optimized strategies
    """

    _instance: MemoryFabricService | None = None

    def __init__(self, settings: Settings):
        self._initialized = False
        self._vram_cache: Any = None

        if _MEMORY_FABRIC_AVAILABLE:
            config = FabricConfig(
                max_entries_per_layer=getattr(settings, "memory_fabric_max_entries", 5000),
                enable_auto_prune=getattr(settings, "memory_fabric_auto_prune", True),
            )
            self._fabric = MemoryFabric.get_or_create(config)
            self._initialized = True
        else:
            self._fabric = None
            logger.warning("memory_fabric_unavailable", reason="package_not_installed")

        # Attempt to wire up the GPU VRAM cache from the workload router
        try:
            from app.routers.gpu import get_workload_router
            wr = get_workload_router()
            if wr is not None:
                cache = wr.get_vram_cache()
                if cache is not None:
                    self._vram_cache = cache
                    logger.info("memory_fabric_vram_cache_wired")
        except Exception:
            pass

    @classmethod
    def initialize(cls, settings: Settings) -> MemoryFabricService:
        cls._instance = cls(settings)
        return cls._instance

    @classmethod
    def get(cls) -> MemoryFabricService:
        if cls._instance is None:
            raise RuntimeError("MemoryFabricService not initialized")
        return cls._instance

    def _ensure_available(self) -> None:
        """Raise if the underlying MemoryFabric is not available."""
        if self._fabric is None:
            raise RuntimeError("MemoryFabric is not available — package not installed")

    def _empty_status(self) -> dict:
        """Return a default status when fabric is unavailable."""
        return {
            "initialized": False,
            "available": False,
            "layers": ["episodic", "semantic", "procedural"],
            "totalEntries": 0,
            "entriesPerLayer": {},
            "reason": "memory-fabric package not installed",
        }

    def store(
        self,
        content: str,
        layer: str = "episodic",
        tags: list[str] | None = None,
        source: str = "",
        importance: float = 0.5,
        confidence: float = 0.8,
        metadata: dict | None = None,
    ) -> dict:
        """Store a memory entry with optional GPU embedding cache."""
        self._ensure_available()
        entry = self._fabric.store(
            content=content,
            layer=layer,
            tags=tags,
            source=source,
            importance=importance,
            confidence=confidence,
            metadata=metadata,
        )

        # Warm the GPU VRAM cache in the background
        if self._vram_cache is not None and content:
            import asyncio
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(self._vram_cache.get_or_compute(content))
            except RuntimeError:
                asyncio.ensure_future(self._vram_cache.get_or_compute(content))

        return entry.to_dict()

    def get_entry(self, entry_id: str) -> dict | None:
        """Get a specific memory entry."""
        self._ensure_available()
        entry = self._fabric.get(entry_id)
        return entry.to_dict() if entry else None

    async def search(self, text: str, layer: str | None = None, limit: int = 20) -> list[dict]:
        """Search memory by text content — uses GPU VRAM cache for fast similarity."""
        self._ensure_available()

        # If GPU VRAM cache is available, use it for accelerated search
        if self._vram_cache is not None and self._vram_cache.is_available:
            try:
                results = await self._vram_cache.search(text, top_k=limit)
                if results:
                    # Map GPU cache results to fabric entries
                    ranked = []
                    for r in results:
                        hash_val = r.get("hash", "")
                        score = r.get("score", 0.0)
                        # Look up by hash in fabric entries
                        for entry in self._fabric._entries.values():
                            entry_hash = self._hash_entry_content(entry.content)
                            if entry_hash == hash_val:
                                d = entry.to_dict()
                                d["gpu_score"] = score
                                ranked.append(d)
                                break
                    if ranked:
                        ranked.sort(key=lambda x: x.get("gpu_score", 0), reverse=True)
                        return ranked[:limit]
            except Exception:
                pass

        # Fall back to standard fabric text search
        return self._fabric.search(text, layer=layer, limit=limit)

    def query(
        self,
        text: str = "",
        layers: list[str] | None = None,
        tags: list[str] | None = None,
        min_importance: float = 0.0,
        limit: int = 20,
        source: str | None = None,
    ) -> list[dict]:
        """Query memory with multiple filters."""
        self._ensure_available()
        query = MemoryQuery(
            text=text,
            layers=[MemoryLayer(l) for l in (layers or ["episodic", "semantic", "procedural"])],
            tags=tags or [],
            min_importance=min_importance,
            limit=limit,
            source=source,
        )
        return self._fabric.query(query)

    def cross_layer_query(self, topic: str, limit_per_layer: int = 5) -> dict:
        """Query all three layers for a topic."""
        self._ensure_available()
        return self._fabric.cross_layer_query(topic, limit_per_layer)

    def get_recent(self, layer: str | None = None, limit: int = 10) -> list[dict]:
        """Get recent entries."""
        self._ensure_available()
        return self._fabric.get_recent(layer=layer, limit=limit)

    def get_by_source(self, source: str, limit: int = 20) -> list[dict]:
        """Get entries from a specific source."""
        self._ensure_available()
        return self._fabric.get_by_source(source, limit=limit)

    def prune(self) -> dict:
        """Prune stale/low-importance entries."""
        self._ensure_available()
        removed = self._fabric.prune()
        return {"pruned": removed, "remaining": self._fabric.stats()["totalEntries"]}

    def stats(self) -> dict:
        """Get memory fabric statistics."""
        if self._fabric is None:
            return self._empty_status()
        return self._fabric.stats()

    async def get_status(self) -> dict:
        stats = self.stats()
        stats.update({
            "initialized": self._initialized,
            "layers": ["episodic", "semantic", "procedural"],
        })
        # Append VRAM cache status if available
        if self._vram_cache is not None and self._vram_cache.is_available:
            try:
                cache_stats = await self._vram_cache.get_stats()
                stats["vramCache"] = cache_stats
            except Exception:
                pass
        return stats

    @staticmethod
    def _hash_entry_content(content: str) -> str:
        import hashlib
        return hashlib.sha256(content.encode("utf-8")).hexdigest()[:16]
