"""
Memory-Driven Evolution Service

Stores and learns from:
  - Successful execution traces → reusable patterns
  - Failed executions → anti-patterns to avoid
  - User preferences → personalized behavior
  - Optimal routing decisions → better future routing

Every interaction feeds back into the system to improve future performance.
"""
from __future__ import annotations

import json
import time
from collections import defaultdict
from typing import Any
from uuid import uuid4

from app.core.logging import get_logger

logger = get_logger(__name__)

# In-memory store (in production, use Redis/PostgreSQL)
_evolution_store: dict[str, list[dict]] = {
    "successful_patterns": [],
    "failed_patterns": [],
    "routing_decisions": [],
    "user_preferences": [],
    "optimization_tips": [],
}


class EvolutionService:
    """
    Learns from every task execution to improve future performance.
    """

    _instance: EvolutionService | None = None

    def __init__(self):
        self._patterns: dict[str, list[dict]] = defaultdict(list)

    @classmethod
    def initialize(cls) -> EvolutionService:
        cls._instance = cls()
        return cls._instance

    @classmethod
    def get(cls) -> EvolutionService:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    # ── Recording ─────────────────────────────────────────────────────────────

    def record_execution(
        self,
        task: str,
        task_type: str,
        success: bool,
        output: str = "",
        model_used: str = "",
        sector_brain_used: str | None = None,
        confidence: float = 0.0,
        latency_ms: float = 0.0,
        error: str | None = None,
        metadata: dict | None = None,
    ) -> str:
        """Record a task execution for future learning."""
        record_id = f"ev_{uuid4().hex[:8]}"
        record = {
            "id": record_id,
            "task": task[:500],
            "taskType": task_type,
            "success": success,
            "output": output[:500] if output else "",
            "modelUsed": model_used,
            "sectorBrainUsed": sector_brain_used,
            "confidence": confidence,
            "latencyMs": latency_ms,
            "error": error,
            "metadata": metadata or {},
            "timestamp": time.time(),
        }

        if success:
            self._patterns["successful_patterns"].append(record)
            # Keep max 200 successful patterns
            if len(self._patterns["successful_patterns"]) > 200:
                self._patterns["successful_patterns"].pop(0)
        else:
            self._patterns["failed_patterns"].append(record)
            # Keep max 100 failed patterns
            if len(self._patterns["failed_patterns"]) > 100:
                self._patterns["failed_patterns"].pop(0)

        # Always store routing decisions
        self._patterns["routing_decisions"].append({
            "id": record_id,
            "taskType": task_type,
            "modelUsed": model_used,
            "sectorBrainUsed": sector_brain_used,
            "success": success,
            "confidence": confidence,
            "latencyMs": latency_ms,
            "timestamp": time.time(),
        })
        if len(self._patterns["routing_decisions"]) > 500:
            self._patterns["routing_decisions"].pop(0)

        return record_id

    def record_user_preference(
        self,
        key: str,
        value: Any,
        source: str = "inference",
    ) -> None:
        """Record a user preference or behavioral pattern."""
        self._patterns["user_preferences"].append({
            "key": key,
            "value": value,
            "source": source,
            "timestamp": time.time(),
        })

    # ── Learning / Retrieval ──────────────────────────────────────────────────

    def get_similar_successful_patterns(
        self,
        task: str,
        task_type: str | None = None,
        top_k: int = 3,
    ) -> list[dict]:
        """Find similar successful executions by task type and keyword overlap."""
        candidates = self._patterns["successful_patterns"]

        if task_type:
            candidates = [c for c in candidates if c["taskType"] == task_type]

        # Simple keyword overlap scoring
        task_lower = task.lower()
        task_words = set(task_lower.split())

        scored = []
        for c in candidates:
            c_task_lower = c["task"].lower()
            c_words = set(c_task_lower.split())
            overlap = len(task_words & c_words)
            if overlap > 0:
                scored.append((overlap / max(len(task_words | c_words), 1), c))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [s[1] for s in scored[:top_k]]

    def get_best_routing_for_task_type(self, task_type: str) -> dict[str, Any] | None:
        """Find the most successful routing configuration for a task type."""
        decisions = [
            d for d in self._patterns["routing_decisions"]
            if d["taskType"] == task_type
        ]
        if not decisions:
            return None

        # Group by (model, sector_brain) pair
        configs: dict[str, dict] = {}
        for d in decisions:
            key = f"{d['modelUsed']}|{d['sectorBrainUsed']}"
            if key not in configs:
                configs[key] = {
                    "modelUsed": d["modelUsed"],
                    "sectorBrainUsed": d["sectorBrainUsed"],
                    "attempts": 0,
                    "successes": 0,
                    "avgConfidence": 0.0,
                    "avgLatencyMs": 0.0,
                }
            cfg = configs[key]
            cfg["attempts"] += 1
            if d["success"]:
                cfg["successes"] += 1
            cfg["avgConfidence"] = (cfg["avgConfidence"] * (cfg["attempts"] - 1) + d["confidence"]) / cfg["attempts"]
            cfg["avgLatencyMs"] = (cfg["avgLatencyMs"] * (cfg["attempts"] - 1) + d["latencyMs"]) / cfg["attempts"]

        # Find best config by win rate
        best = max(configs.values(), key=lambda c: c["successes"] / max(c["attempts"], 1))
        best["taskType"] = task_type
        return best

    def get_optimization_suggestions(self) -> list[str]:
        """Generate optimization suggestions based on execution history."""
        suggestions = []

        # Check failed patterns
        failed = self._patterns["failed_patterns"]
        if failed:
            common_errors = defaultdict(int)
            for f in failed:
                if f.get("error"):
                    common_errors[f["error"][:100]] += 1
            if common_errors:
                top_error = max(common_errors, key=common_errors.get)
                if common_errors[top_error] >= 3:
                    suggestions.append(
                        f"Recurring error pattern ({common_errors[top_error]}x): '{top_error}' — "
                        "consider routing these tasks to a different model or sector brain."
                    )

        # Check routing effectiveness
        routing = self._patterns["routing_decisions"]
        if routing:
            success_rate = sum(1 for r in routing if r["success"]) / max(len(routing), 1)
            if success_rate < 0.7:
                suggestions.append(
                    f"Overall routing success rate is {success_rate:.0%}. "
                    "Consider reviewing Smart Router configurations."
                )

        return suggestions

    # ── Status ────────────────────────────────────────────────────────────────

    def get_status(self) -> dict[str, Any]:
        return {
            "successfulPatterns": len(self._patterns["successful_patterns"]),
            "failedPatterns": len(self._patterns["failed_patterns"]),
            "routingDecisions": len(self._patterns["routing_decisions"]),
            "userPreferences": len(self._patterns["user_preferences"]),
            "optimizationSuggestions": self.get_optimization_suggestions(),
            "bestRoutingByType": {
                "code": self.get_best_routing_for_task_type("code"),
                "research": self.get_best_routing_for_task_type("research"),
                "general": self.get_best_routing_for_task_type("general"),
            },
        }

    def get_all(self) -> dict[str, list[dict]]:
        return dict(self._patterns)
