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
        """Store a memory entry."""
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
        return entry.to_dict()

    def get_entry(self, entry_id: str) -> dict | None:
        """Get a specific memory entry."""
        self._ensure_available()
        entry = self._fabric.get(entry_id)
        return entry.to_dict() if entry else None

    def search(self, text: str, layer: str | None = None, limit: int = 20) -> list[dict]:
        """Search memory by text content."""
        self._ensure_available()
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

    def get_status(self) -> dict:
        stats = self.stats()
        stats.update({
            "initialized": self._initialized,
            "layers": ["episodic", "semantic", "procedural"],
        })
        return stats
