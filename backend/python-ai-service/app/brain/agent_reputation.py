"""
Agent Reputation System — tracks performance metrics and trust scores for every agent and brain.

Each agent/brain maintains:
  - trust_score: overall reliability (0.0–1.0)
  - win_rate: fraction of successful completions
  - avg_confidence: mean self-reported confidence
  - avg_latency_ms: mean response time
  - cost_efficiency: output quality per unit cost
  - specialization_score: performance on specific task types

The Macro Brain uses these scores to route tasks to the best agent.
"""
from __future__ import annotations

import json
import time
from collections import defaultdict
from typing import Any

from app.core.logging import get_logger

logger = get_logger(__name__)


class AgentReputationRecord:
    """Performance record for a single agent or brain."""

    def __init__(self, agent_id: str, agent_type: str = "agent"):
        self.agent_id = agent_id
        self.agent_type = agent_type  # "agent", "brain", "sector_brain"
        self.total_tasks = 0
        self.successful_tasks = 0
        self.failed_tasks = 0
        self.total_confidence = 0.0
        self.total_latency_ms = 0.0
        self.total_cost_estimate = 0.0
        self.task_type_results: dict[str, dict] = defaultdict(
            lambda: {"attempts": 0, "successes": 0, "total_confidence": 0.0}
        )
        self.created_at = time.time()
        self.last_updated = time.time()

    @property
    def win_rate(self) -> float:
        if self.total_tasks == 0:
            return 0.0
        return round(self.successful_tasks / self.total_tasks, 4)

    @property
    def trust_score(self) -> float:
        """Weighted composite: win_rate weighted 70%, confidence 30%."""
        if self.total_tasks == 0:
            return 0.5  # neutral starting score
        wr = self.win_rate
        avg_conf = self.total_confidence / self.total_tasks if self.total_tasks > 0 else 0.0
        return round(0.7 * wr + 0.3 * avg_conf, 4)

    @property
    def avg_confidence(self) -> float:
        if self.total_tasks == 0:
            return 0.0
        return round(self.total_confidence / self.total_tasks, 4)

    @property
    def avg_latency_ms(self) -> float:
        if self.total_tasks == 0:
            return 0.0
        return round(self.total_latency_ms / self.total_tasks, 1)

    def record_task(
        self,
        success: bool,
        confidence: float = 0.0,
        latency_ms: float = 0.0,
        cost_estimate: float = 0.0,
        task_type: str = "general",
    ) -> None:
        self.total_tasks += 1
        if success:
            self.successful_tasks += 1
        else:
            self.failed_tasks += 1
        self.total_confidence += confidence
        self.total_latency_ms += latency_ms
        self.total_cost_estimate += cost_estimate
        self.last_updated = time.time()

        # Per-task-type tracking
        ttr = self.task_type_results[task_type]
        ttr["attempts"] += 1
        if success:
            ttr["successes"] += 1
        ttr["total_confidence"] += confidence

    def get_specialization_score(self, task_type: str) -> float:
        """Return the win rate for a specific task type, or 0 if no data."""
        ttr = self.task_type_results.get(task_type)
        if not ttr or ttr["attempts"] == 0:
            return 0.0
        return round(ttr["successes"] / ttr["attempts"], 4)

    def to_dict(self) -> dict[str, Any]:
        return {
            "agentId": self.agent_id,
            "agentType": self.agent_type,
            "trustScore": self.trust_score,
            "winRate": self.win_rate,
            "avgConfidence": self.avg_confidence,
            "avgLatencyMs": self.avg_latency_ms,
            "totalTasks": self.total_tasks,
            "successfulTasks": self.successful_tasks,
            "failedTasks": self.failed_tasks,
            "totalCostEstimate": round(self.total_cost_estimate, 4),
            "specializations": {
                ttype: round(data["successes"] / max(data["attempts"], 1), 4)
                for ttype, data in self.task_type_results.items()
            },
            "createdAt": self.created_at,
            "lastUpdated": self.last_updated,
        }


class AgentReputation:
    """
    Central reputation tracker. Maintains records for all agents and brains,
    providing ranking and routing recommendations.
    """

    _instance: AgentReputation | None = None

    def __init__(self):
        self._records: dict[str, AgentReputationRecord] = {}

    @classmethod
    def initialize(cls) -> AgentReputation:
        cls._instance = cls()
        return cls._instance

    @classmethod
    def get(cls) -> AgentReputation:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def get_or_create(self, agent_id: str, agent_type: str = "agent") -> AgentReputationRecord:
        if agent_id not in self._records:
            self._records[agent_id] = AgentReputationRecord(agent_id, agent_type)
        return self._records[agent_id]

    def record(
        self,
        agent_id: str,
        success: bool,
        confidence: float = 0.0,
        latency_ms: float = 0.0,
        cost_estimate: float = 0.0,
        task_type: str = "general",
        agent_type: str = "agent",
    ) -> AgentReputationRecord:
        record = self.get_or_create(agent_id, agent_type)
        record.record_task(success, confidence, latency_ms, cost_estimate, task_type)
        return record

    def get_ranking(self, min_tasks: int = 0, agent_type: str | None = None) -> list[dict]:
        """Return agents sorted by trust_score descending."""
        candidates = [
            r for r in self._records.values()
            if r.total_tasks >= min_tasks
            and (agent_type is None or r.agent_type == agent_type)
        ]
        candidates.sort(key=lambda r: r.trust_score, reverse=True)
        return [r.to_dict() for r in candidates]

    def get_best_for_task(self, task_type: str, min_tasks: int = 2) -> AgentReputationRecord | None:
        """Find the agent with the highest specialization score for a task type."""
        candidates = [
            r for r in self._records.values()
            if r.total_tasks >= min_tasks
            and r.get_specialization_score(task_type) > 0
        ]
        if not candidates:
            return None
        candidates.sort(key=lambda r: r.get_specialization_score(task_type), reverse=True)
        return candidates[0]

    def get_record(self, agent_id: str) -> dict | None:
        r = self._records.get(agent_id)
        return r.to_dict() if r else None

    def get_all_records(self) -> list[dict]:
        return [r.to_dict() for r in self._records.values()]
