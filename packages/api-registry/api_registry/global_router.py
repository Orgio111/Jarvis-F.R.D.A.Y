"""
GlobalRouter — Self-learning AI routing system with performance tracking.

Extends the API registry with:
  - Performance tracking per provider (latency, cost, accuracy)
  - Self-learning: automatically optimizes routing based on tracked metrics
  - Model routing decisions (FAST / SMART / HEAVY / SPECIALIZED)
  - Cost-aware fallback chains
  - Confidence-based dispatch

This is the "Global Router" component from the v3 architecture,
connecting model selection, API routing, and workflow dispatching
into a unified, self-optimizing system.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable
from uuid import uuid4


class RoutingMode(Enum):
    """Routing modes matching the v3 architecture model tiers."""

    FAST = "fast"        # Simple queries, routing decisions
    SMART = "smart"      # Reasoning, planning, moderate tasks
    HEAVY = "heavy"      # Architecture, coding, deep analysis
    SPECIALIZED = "specialized"  # Vision, speech, embeddings


class RoutingStrategy(Enum):
    """Strategies for selecting the best provider/route."""

    LATENCY = "latency"          # Pick fastest
    COST = "cost"                # Pick cheapest
    CONFIDENCE = "confidence"    # Pick most reliable (highest confidence)
    BALANCED = "balanced"        # Weighted composite
    ROUND_ROBIN = "round_robin"  # Distribute load
    FALLBACK_CHAIN = "fallback"  # Try providers in order


@dataclass
class RoutePerformanceRecord:
    """Performance metrics for a single route/provider combination."""

    route_id: str
    provider_name: str
    model: str = ""
    total_calls: int = 0
    successful_calls: int = 0
    failed_calls: int = 0
    total_latency_ms: float = 0.0
    total_cost: float = 0.0
    avg_confidence: float = 0.0
    last_called_at: float = 0.0
    first_called_at: float = 0.0

    @property
    def success_rate(self) -> float:
        return self.successful_calls / max(self.total_calls, 1)

    @property
    def avg_latency_ms(self) -> float:
        return self.total_latency_ms / max(self.total_calls, 1)

    @property
    def avg_cost(self) -> float:
        return self.total_cost / max(self.total_calls, 1)

    @property
    def composite_score(self) -> float:
        """Weighted score for route selection (0-1, higher = better)."""
        success_score = self.success_rate * 0.4
        latency_score = max(0.0, 1.0 - self.avg_latency_ms / 5000.0) * 0.25
        cost_score = max(0.0, 1.0 - self.avg_cost / 1.0) * 0.15
        confidence_score = self.avg_confidence * 0.2
        return success_score + latency_score + cost_score + confidence_score

    def record_call(self, success: bool, latency_ms: float, cost: float = 0.0, confidence: float = 0.0) -> None:
        self.total_calls += 1
        if success:
            self.successful_calls += 1
        else:
            self.failed_calls += 1
        self.total_latency_ms += latency_ms
        self.total_cost += cost
        self.avg_confidence = (self.avg_confidence * (self.total_calls - 1) + confidence) / self.total_calls
        self.last_called_at = time.time()
        if self.first_called_at == 0.0:
            self.first_called_at = time.time()

    def to_dict(self) -> dict[str, Any]:
        return {
            "routeId": self.route_id,
            "providerName": self.provider_name,
            "model": self.model,
            "totalCalls": self.total_calls,
            "successfulCalls": self.successful_calls,
            "failedCalls": self.failed_calls,
            "successRate": round(self.success_rate, 3),
            "avgLatencyMs": round(self.avg_latency_ms, 1),
            "avgCost": round(self.avg_cost, 4),
            "avgConfidence": round(self.avg_confidence, 3),
            "compositeScore": round(self.composite_score, 3),
            "lastCalledAt": self.last_called_at,
        }


@dataclass
class RoutingDecision:
    """Result of a routing decision."""

    selected_route_id: str
    selected_provider: str
    mode: RoutingMode
    strategy: RoutingStrategy
    confidence: float
    alternatives: list[str] = field(default_factory=list)
    reason: str = ""
    timestamp: float = 0.0
    decision_id: str = field(default_factory=lambda: f"route_{uuid4().hex[:8]}")

    def to_dict(self) -> dict[str, Any]:
        return {
            "decisionId": self.decision_id,
            "selectedRoute": self.selected_route_id,
            "selectedProvider": self.selected_provider,
            "mode": self.mode.value,
            "strategy": self.strategy.value,
            "confidence": round(self.confidence, 3),
            "alternatives": self.alternatives,
            "reason": self.reason,
            "timestamp": self.timestamp or time.time(),
        }


class GlobalRouter:
    """
    Self-learning AI routing system.

    Features:
      - Performance tracking for every route/provider/model combination
      - Self-learning: automatically optimizes routing strategy
      - Mode-based routing (FAST / SMART / HEAVY / SPECIALIZED)
      - Multiple selection strategies (latency, cost, confidence, balanced)
      - Automatic fallback chains
      - Route performance analytics
    """

    _instance: GlobalRouter | None = None

    def __init__(self):
        self._records: dict[str, RoutePerformanceRecord] = {}
        self._routes: dict[str, dict[str, Any]] = {}  # route_id → metadata
        self._mode_mappings: dict[str, list[str]] = {
            "fast": [],
            "smart": [],
            "heavy": [],
            "specialized": [],
        }
        self._default_strategy = RoutingStrategy.BALANCED
        self._learning_enabled = True
        self._min_calls_before_learning = 10

    @classmethod
    def get_or_create(cls) -> GlobalRouter:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset(cls) -> None:
        cls._instance = None

    # ─── Route Registration ──────────────────────────────────────────────────

    def register_route(
        self,
        route_id: str,
        provider_name: str,
        model: str = "",
        mode: str = "smart",
        metadata: dict | None = None,
    ) -> None:
        """Register a route for routing decisions."""
        self._routes[route_id] = {
            "routeId": route_id,
            "providerName": provider_name,
            "model": model,
            "mode": mode,
            "metadata": metadata or {},
        }
        if route_id not in self._records:
            self._records[route_id] = RoutePerformanceRecord(
                route_id=route_id,
                provider_name=provider_name,
                model=model,
            )

        # Add to mode mapping
        if mode in self._mode_mappings:
            if route_id not in self._mode_mappings[mode]:
                self._mode_mappings[mode].append(route_id)

    def unregister_route(self, route_id: str) -> None:
        """Remove a route from the router."""
        self._routes.pop(route_id, None)
        self._records.pop(route_id, None)
        for mode in self._mode_mappings:
            if route_id in self._mode_mappings[mode]:
                self._mode_mappings[mode].remove(route_id)

    # ─── Routing Decisions ──────────────────────────────────────────────────

    def select_route(
        self,
        mode: str | RoutingMode = RoutingMode.SMART,
        strategy: str | RoutingStrategy = RoutingStrategy.BALANCED,
        preferred_provider: str | None = None,
        exclude_route_ids: list[str] | None = None,
    ) -> RoutingDecision:
        """
        Select the best route for the given mode and strategy.

        Uses performance records to make self-learning decisions.
        """
        if isinstance(mode, str):
            mode = RoutingMode(mode)
        if isinstance(strategy, str):
            strategy = RoutingStrategy(strategy)

        # Get candidates for this mode
        candidates = self._mode_mappings.get(mode.value, [])
        if not candidates:
            # Fallback: use all routes
            candidates = list(self._routes.keys())

        # Exclude specified routes
        if exclude_route_ids:
            candidates = [r for r in candidates if r not in exclude_route_ids]

        if not candidates:
            return RoutingDecision(
                selected_route_id="",
                selected_provider="none",
                mode=mode,
                strategy=strategy,
                confidence=0.0,
                reason="No routes available",
            )

        # If preferred provider specified, prioritize
        if preferred_provider:
            preferred = [r for r in candidates if self._routes.get(r, {}).get("providerName") == preferred_provider]
            if preferred:
                candidates = preferred

        # Score candidates based on strategy
        scored = []
        for route_id in candidates:
            record = self._records.get(route_id)
            route_info = self._routes.get(route_id, {})

            if not record or record.total_calls < self._min_calls_before_learning:
                # Not enough data yet — give default score
                base_score = 0.5
            else:
                base_score = record.composite_score

            if strategy == RoutingStrategy.LATENCY:
                score = 1.0 - (record.avg_latency_ms / 10000.0) if record and record.total_calls > 0 else 0.5
            elif strategy == RoutingStrategy.COST:
                score = 1.0 - (record.avg_cost / 1.0) if record and record.total_calls > 0 else 0.5
            elif strategy == RoutingStrategy.CONFIDENCE:
                score = record.avg_confidence if record else 0.5
            elif strategy == RoutingStrategy.BALANCED:
                score = record.composite_score if record and record.total_calls >= self._min_calls_before_learning else 0.5
            elif strategy == RoutingStrategy.ROUND_ROBIN:
                score = -record.total_calls if record else 0  # Least-used first
            else:  # FALLBACK_CHAIN
                score = 1.0 - (len(scored) * 0.1)  # Order matters

            # Boost recently working routes slightly
            if record and record.last_called_at > 0:
                time_since_call = time.time() - record.last_called_at
                if time_since_call < 60 and record.success_rate > 0.8:
                    score += 0.05

            scored.append((route_id, min(score, 1.0)))

        # Sort by score descending
        scored.sort(key=lambda x: x[1], reverse=True)

        best_route_id = scored[0][0]
        best_score = scored[0][1]
        best_route = self._routes.get(best_route_id, {})

        alternative_ids = [r for r, _ in scored[1:4]]
        alternatives = [
            self._routes.get(r, {}).get("providerName", r) for r in alternative_ids
        ]

        return RoutingDecision(
            selected_route_id=best_route_id,
            selected_provider=best_route.get("providerName", "unknown"),
            mode=mode,
            strategy=strategy,
            confidence=best_score,
            alternatives=alternatives,
            reason=f"Selected {best_route.get('providerName', best_route_id)} from {len(scored)} candidates (score: {best_score:.3f})",
            timestamp=time.time(),
        )

    def select_mode(self, task: str, task_complexity: float = 0.5) -> RoutingMode:
        """
        Select the appropriate routing mode based on task description and complexity.

        task_complexity: 0.0 (trivial) to 1.0 (extremely complex)
        """
        task_lower = task.lower()

        # Detect specialized tasks
        if any(word in task_lower for word in ["image", "vision", "vision", "speech", "audio", "embedding"]):
            return RoutingMode.SPECIALIZED

        # Detect heavy/coding tasks
        if task_complexity > 0.8 or any(word in task_lower for word in ["architecture", "system design", "refactor", "complex"]):
            return RoutingMode.HEAVY

        # Detect smart/reasoning tasks
        if task_complexity > 0.4 or any(word in task_lower for word in ["reason", "plan", "analyze", "compare", "evaluate"]):
            return RoutingMode.SMART

        # Default: FAST for simple tasks
        return RoutingMode.FAST

    # ─── Performance Recording ──────────────────────────────────────────────

    def record_result(
        self,
        route_id: str,
        success: bool,
        latency_ms: float = 0.0,
        cost: float = 0.0,
        confidence: float = 0.0,
    ) -> None:
        """Record the result of a routing decision for self-learning."""
        if route_id not in self._records:
            return

        self._records[route_id].record_call(success, latency_ms, cost, confidence)

    def get_route_performance(self, route_id: str) -> dict | None:
        """Get performance data for a specific route."""
        record = self._records.get(route_id)
        return record.to_dict() if record else None

    def get_best_routes(self, mode: str | None = None, limit: int = 10) -> list[dict]:
        """Get the best performing routes, optionally filtered by mode."""
        candidates = list(self._records.values())
        if mode:
            route_ids = self._mode_mappings.get(mode, [])
            candidates = [r for r in candidates if r.route_id in route_ids]

        candidates.sort(key=lambda r: r.composite_score, reverse=True)
        return [r.to_dict() for r in candidates[:limit]]

    def get_performance_summary(self) -> dict[str, Any]:
        """Get overall routing performance summary."""
        all_records = list(self._records.values())
        if not all_records:
            return {"status": "no_data"}

        total_calls = sum(r.total_calls for r in all_records)
        successful = sum(r.successful_calls for r in all_records)
        avg_latency = sum(r.total_latency_ms for r in all_records) / max(len(all_records), 1)
        avg_score = sum(r.composite_score for r in all_records) / max(len(all_records), 1)

        return {
            "totalRoutes": len(self._routes),
            "totalCalls": total_calls,
            "successfulCalls": successful,
            "successRate": round(successful / max(total_calls, 1), 3),
            "avgLatencyMs": round(avg_latency, 1),
            "avgCompositeScore": round(avg_score, 3),
            "routesByMode": {mode: len(route_ids) for mode, route_ids in self._mode_mappings.items()},
            "learningEnabled": self._learning_enabled,
        }

    # ─── Configuration ────────────────────────────────────────────────────

    def set_strategy(self, strategy: RoutingStrategy | str) -> None:
        if isinstance(strategy, str):
            strategy = RoutingStrategy(strategy)
        self._default_strategy = strategy

    def enable_learning(self, enabled: bool = True) -> None:
        self._learning_enabled = enabled

    def set_min_calls_for_learning(self, min_calls: int) -> None:
        self._min_calls_before_learning = max(1, min_calls)

    def get_status(self) -> dict[str, Any]:
        return {
            "totalRoutes": len(self._routes),
            "totalRecords": len(self._records),
            "defaultStrategy": self._default_strategy.value,
            "learningEnabled": self._learning_enabled,
            "minCallsForLearning": self._min_calls_before_learning,
            "performanceSummary": self.get_performance_summary(),
        }
