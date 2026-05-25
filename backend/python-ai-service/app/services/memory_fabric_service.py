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
from memory_fabric.fabric import (
    FabricConfig,
    MemoryFabric,
    MemoryLayer,
    MemoryQuery,
)

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
        config = FabricConfig(
            max_entries_per_layer=settings.get("memory_fabric_max_entries", 5000),
            enable_auto_prune=settings.get("memory_fabric_auto_prune", True),
        )
        self._fabric = MemoryFabric.get_or_create(config)
        self._initialized = True

    @classmethod
    def initialize(cls, settings: Settings) -> MemoryFabricService:
        cls._instance = cls(settings)
        return cls._instance

    @classmethod
    def get(cls) -> MemoryFabricService:
        if cls._instance is None:
            raise RuntimeError("MemoryFabricService not initialized")
        return cls._instance

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

    def get(self, entry_id: str) -> dict | None:
        """Get a specific memory entry."""
        entry = self._fabric.get(entry_id)
        return entry.to_dict() if entry else None

    def search(self, text: str, layer: str | None = None, limit: int = 20) -> list[dict]:
        """Search memory by text content."""
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
        return self._fabric.cross_layer_query(topic, limit_per_layer)

    def get_recent(self, layer: str | None = None, limit: int = 10) -> list[dict]:
        """Get recent entries."""
        return self._fabric.get_recent(layer=layer, limit=limit)

    def get_by_source(self, source: str, limit: int = 20) -> list[dict]:
        """Get entries from a specific source."""
        return self._fabric.get_by_source(source, limit=limit)

    def prune(self) -> dict:
        """Prune stale/low-importance entries."""
        removed = self._fabric.prune()
        return {"pruned": removed, "remaining": self._fabric.stats()["totalEntries"]}

    def stats(self) -> dict:
        """Get memory fabric statistics."""
        return self._fabric.stats()

    def get_status(self) -> dict:
        stats = self.stats()
        stats.update({
            "initialized": self._initialized,
            "layers": ["episodic", "semantic", "procedural"],
        })
        return stats
