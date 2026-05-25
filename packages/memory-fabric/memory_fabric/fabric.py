"""
MemoryFabric — Multi-layered cognitive memory for autonomous AI systems.

Provides three distinct memory layers:
  - Episodic:   what happened (past executions, conversations, workflow traces)
  - Semantic:   what is true (concepts, embeddings, architecture knowledge)
  - Procedural: how to do it (successful patterns, optimized strategies)

All layers support:
  - Store / Retrieve / Search / Prune operations
  - Time-weighted decay for automatic forgetting
  - Cross-layer queries for composite recall
  - Confidence scoring on retrieval
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any
from uuid import uuid4


class MemoryLayer(Enum):
    """The three cognitive memory layers."""

    EPISODIC = "episodic"
    SEMANTIC = "semantic"
    PROCEDURAL = "procedural"


@dataclass
class MemoryEntry:
    """A single memory entry in any layer."""

    entry_id: str = field(default_factory=lambda: f"mem_{uuid4().hex[:10]}")
    layer: MemoryLayer = MemoryLayer.EPISODIC
    content: str = ""
    tags: list[str] = field(default_factory=list)
    source: str = ""  # e.g., "macro_brain", "research_swarm", "user_chat"
    importance: float = 0.5  # 0.0 (trivial) – 1.0 (critical)
    confidence: float = 0.8
    timestamp: float = 0.0
    last_accessed: float = 0.0
    access_count: int = 0
    embedding: list[float] | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    ttl_seconds: float = 0.0  # 0 = never expires
    parent_id: str | None = None  # For linking related memories

    @property
    def age_seconds(self) -> float:
        return time.time() - self.timestamp

    @property
    def relevance_score(self) -> float:
        """Calculate a relevance score combining importance, recency, and access frequency."""
        recency_factor = 1.0 / (1.0 + self.age_seconds / 3600.0)  # decays over hours
        frequency_factor = min(self.access_count / 10.0, 1.0)
        return self.importance * 0.5 + recency_factor * 0.3 + frequency_factor * 0.2

    def to_dict(self) -> dict[str, Any]:
        return {
            "entryId": self.entry_id,
            "layer": self.layer.value,
            "content": self.content[:500],
            "tags": self.tags,
            "source": self.source,
            "importance": round(self.importance, 2),
            "confidence": round(self.confidence, 2),
            "timestamp": self.timestamp,
            "ageSeconds": round(self.age_seconds, 1),
            "accessCount": self.access_count,
            "relevanceScore": round(self.relevance_score, 3),
            "metadata": {k: str(v)[:100] for k, v in self.metadata.items()},
        }


@dataclass
class MemoryQuery:
    """A query against the memory fabric."""

    text: str = ""
    layers: list[MemoryLayer] = field(default_factory=lambda: list(MemoryLayer))
    tags: list[str] = field(default_factory=list)
    min_importance: float = 0.0
    min_confidence: float = 0.0
    max_age_seconds: float = 0.0  # 0 = no limit
    limit: int = 20
    source: str | None = None


@dataclass
class FabricConfig:
    """Configuration for the memory fabric."""

    max_entries_per_layer: int = 5000
    auto_prune_threshold: int = 4000
    importance_decay_factor: float = 0.95  # per day
    default_ttl_episodic: float = 86400 * 7  # 7 days
    default_ttl_semantic: float = 86400 * 90  # 90 days
    default_ttl_procedural: float = 86400 * 365  # 1 year
    enable_auto_prune: bool = True
    prune_interval_seconds: float = 3600  # check every hour


class MemoryFabric:
    """
    Central cognitive memory store with three layers.

    Usage:
        fabric = MemoryFabric.get_or_create()
        entry = fabric.store("User requested weather API integration", layer="episodic")
        results = fabric.search("weather API")
        summary = fabric.cross_layer_query("user preferences")
    """

    _instance: MemoryFabric | None = None

    def __init__(self, config: FabricConfig | None = None):
        self._config = config or FabricConfig()
        self._entries: dict[str, MemoryEntry] = {}
        self._tags_index: dict[str, list[str]] = {}  # tag → [entry_id]
        self._layer_indices: dict[str, list[str]] = {
            "episodic": [],
            "semantic": [],
            "procedural": [],
        }
        self._last_prune: float = 0.0

    @classmethod
    def get_or_create(cls, config: FabricConfig | None = None) -> MemoryFabric:
        if cls._instance is None:
            cls._instance = cls(config)
        return cls._instance

    @classmethod
    def reset(cls) -> None:
        cls._instance = None

    # ─── Store ────────────────────────────────────────────────────────────────

    def store(
        self,
        content: str,
        layer: str | MemoryLayer = "episodic",
        tags: list[str] | None = None,
        source: str = "",
        importance: float = 0.5,
        confidence: float = 0.8,
        ttl_seconds: float | None = None,
        metadata: dict | None = None,
        parent_id: str | None = None,
    ) -> MemoryEntry:
        """Store a new memory entry."""
        if isinstance(layer, str):
            layer = MemoryLayer(layer)

        ttl = ttl_seconds if ttl_seconds is not None else {
            MemoryLayer.EPISODIC: self._config.default_ttl_episodic,
            MemoryLayer.SEMANTIC: self._config.default_ttl_semantic,
            MemoryLayer.PROCEDURAL: self._config.default_ttl_procedural,
        }.get(layer, 0.0)

        entry = MemoryEntry(
            layer=layer,
            content=content,
            tags=tags or [],
            source=source,
            importance=importance,
            confidence=confidence,
            timestamp=time.time(),
            last_accessed=time.time(),
            metadata=metadata or {},
            ttl_seconds=ttl,
            parent_id=parent_id,
        )

        self._entries[entry.entry_id] = entry
        self._layer_indices[layer.value].append(entry.entry_id)

        for tag in (tags or []):
            self._tags_index.setdefault(tag, []).append(entry.entry_id)

        self._auto_prune_if_needed()
        return entry

    # ─── Retrieve ─────────────────────────────────────────────────────────────

    def get(self, entry_id: str) -> MemoryEntry | None:
        """Retrieve a specific memory entry by ID."""
        entry = self._entries.get(entry_id)
        if entry:
            entry.last_accessed = time.time()
            entry.access_count += 1
        return entry

    def query(self, query: MemoryQuery) -> list[dict]:
        """
        Search memory using tags, layer, importance, and age filters.

        Returns scored and sorted results.
        """
        candidates: list[MemoryEntry] = []

        # Collect candidates from requested layers
        for layer in query.layers:
            for eid in self._layer_indices.get(layer.value, []):
                entry = self._entries.get(eid)
                if entry:
                    candidates.append(entry)

        # Apply filters
        filtered = []
        for entry in candidates:
            # Tag filter
            if query.tags and not any(t in entry.tags for t in query.tags):
                continue
            # Importance filter
            if entry.importance < query.min_importance:
                continue
            # Confidence filter
            if entry.confidence < query.min_confidence:
                continue
            # Age filter
            if query.max_age_seconds > 0 and entry.age_seconds > query.max_age_seconds:
                continue
            # Source filter
            if query.source and entry.source != query.source:
                continue

            # Check TTL expiry
            if entry.ttl_seconds > 0 and entry.age_seconds > entry.ttl_seconds:
                continue

            filtered.append(entry)

        # Score by relevance
        filtered.sort(key=lambda e: e.relevance_score, reverse=True)

        results = filtered[:query.limit]
        for entry in results:
            entry.last_accessed = time.time()
            entry.access_count += 1

        return [e.to_dict() for e in results]

    def search(self, text: str, layer: str | None = None, limit: int = 20) -> list[dict]:
        """
        Simple text-based search across memory layers.

        This is a keyword matching search. For semantic search,
        use query() with embeddings.
        """
        text_lower = text.lower()
        query = MemoryQuery(
            text=text,
            limit=limit,
        )
        if layer:
            query.layers = [MemoryLayer(layer)]

        candidates: list[MemoryEntry] = []
        for l in query.layers:
            for eid in self._layer_indices.get(l.value, []):
                entry = self._entries.get(eid)
                if entry and text_lower in entry.content.lower():
                    candidates.append(entry)

        candidates.sort(key=lambda e: e.relevance_score, reverse=True)

        results = candidates[:limit]
        for entry in results:
            entry.last_accessed = time.time()
            entry.access_count += 1

        return [e.to_dict() for e in results]

    def cross_layer_query(self, topic: str, limit_per_layer: int = 5) -> dict[str, list[dict]]:
        """Query all three layers for a topic and return grouped results."""
        return {
            "episodic": self.search(topic, layer="episodic", limit=limit_per_layer),
            "semantic": self.search(topic, layer="semantic", limit=limit_per_layer),
            "procedural": self.search(topic, layer="procedural", limit=limit_per_layer),
        }

    # ─── Pruning ──────────────────────────────────────────────────────────────

    def _auto_prune_if_needed(self) -> None:
        """Check if pruning is needed based on entry count and interval."""
        if not self._config.enable_auto_prune:
            return

        now = time.time()
        if now - self._last_prune < self._config.prune_interval_seconds:
            return

        total = len(self._entries)
        if total <= self._config.auto_prune_threshold:
            return

        self.prune()
        self._last_prune = now

    def prune(self, target_count: int = 0) -> int:
        """
        Remove low-importance, expired, and stale entries.

        Returns number of entries removed.
        """
        if target_count <= 0:
            target_count = self._config.max_entries_per_layer * 3

        removed = 0
        now = time.time()

        to_remove: list[str] = []

        for eid, entry in self._entries.items():
            # Remove expired entries
            if entry.ttl_seconds > 0 and entry.age_seconds > entry.ttl_seconds:
                to_remove.append(eid)
                continue

            # Remove very low importance entries that are old and rarely accessed
            if entry.importance < 0.2 and entry.age_seconds > 86400 and entry.access_count < 2:
                to_remove.append(eid)
                continue

        # If still over capacity, remove lowest relevance
        remaining = len(self._entries) - len(to_remove)
        if remaining > target_count:
            sorted_entries = sorted(
                [e for eid, e in self._entries.items() if eid not in to_remove],
                key=lambda e: e.relevance_score,
            )
            excess = remaining - target_count
            to_remove.extend(e.entry_id for e in sorted_entries[:excess])

        for eid in to_remove:
            entry = self._entries.pop(eid, None)
            if entry:
                # Remove from layer index
                if entry.layer.value in self._layer_indices:
                    if eid in self._layer_indices[entry.layer.value]:
                        self._layer_indices[entry.layer.value].remove(eid)
                # Remove from tags index
                for tag in entry.tags:
                    if tag in self._tags_index and eid in self._tags_index[tag]:
                        self._tags_index[tag].remove(eid)
                removed += 1

        return removed

    # ─── Stats ────────────────────────────────────────────────────────────────

    def stats(self) -> dict[str, Any]:
        """Get memory fabric statistics."""
        counts = {layer: 0 for layer in ["episodic", "semantic", "procedural"]}
        for eid, entry in self._entries.items():
            counts[entry.layer.value] = counts.get(entry.layer.value, 0) + 1

        avg_importance = sum(e.importance for e in self._entries.values()) / max(len(self._entries), 1)
        avg_confidence = sum(e.confidence for e in self._entries.values()) / max(len(self._entries), 1)
        unique_tags = len(self._tags_index)

        return {
            "totalEntries": len(self._entries),
            "entriesByLayer": counts,
            "avgImportance": round(avg_importance, 2),
            "avgConfidence": round(avg_confidence, 2),
            "uniqueTags": unique_tags,
            "lastPrune": self._last_prune,
        }

    def get_recent(self, layer: str | None = None, limit: int = 10) -> list[dict]:
        """Get most recent entries."""
        entries = list(self._entries.values())
        if layer:
            entries = [e for e in entries if e.layer.value == layer]
        entries.sort(key=lambda e: e.timestamp, reverse=True)
        return [e.to_dict() for e in entries[:limit]]

    def get_by_source(self, source: str, limit: int = 20) -> list[dict]:
        """Get entries from a specific source."""
        matching = [e for e in self._entries.values() if e.source == source]
        matching.sort(key=lambda e: e.timestamp, reverse=True)
        return [e.to_dict() for e in matching[:limit]]
