"""
EvolutionEngine — Continuous self-improvement through mutation, scoring, and reinforcement.

Core loop:
  EVALUATE → SCORE → MUTATE → RETRY → REINFORCE

Supports multiple mutation targets:
  - prompt_strategy: system prompts, instructions, persona
  - routing_decision: model selection, fallback chains, priority
  - workflow_pattern: step ordering, parallelization, retry config
  - agent_config: capabilities, thresholds, scaling behavior

Each mutation is tracked as an EvolutionTrial with full metadata
for analysis and rollback.
"""

from __future__ import annotations

import random
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any
from uuid import uuid4


class MutationType(Enum):
    """Types of mutations the evolution engine can perform."""

    PROMPT_STRATEGY = "prompt_strategy"
    ROUTING_DECISION = "routing_decision"
    WORKFLOW_PATTERN = "workflow_pattern"
    AGENT_CONFIG = "agent_config"
    MODEL_SELECTION = "model_selection"
    THRESHOLD_TUNING = "threshold_tuning"
    PARALLELIZATION = "parallelization"


@dataclass
class EvolutionScore:
    """Score for a single evolution trial across multiple dimensions."""

    correctness: float = 0.0  # 0-1: was the output correct
    completeness: float = 0.0  # 0-1: were all requirements met
    efficiency: float = 0.0  # 0-1: time/resources used
    confidence: float = 0.0  # 0-1: model/agent confidence
    latency_ms: float = 0.0  # raw latency
    cost: float = 0.0  # raw cost

    @property
    def composite(self) -> float:
        """Weighted composite score."""
        return (
            self.correctness * 0.35 +
            self.completeness * 0.25 +
            self.efficiency * 0.15 +
            self.confidence * 0.15 +
            max(0.0, 1.0 - self.latency_ms / 10000.0) * 0.05 +
            max(0.0, 1.0 - self.cost / 1.0) * 0.05
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "correctness": round(self.correctness, 3),
            "completeness": round(self.completeness, 3),
            "efficiency": round(self.efficiency, 3),
            "confidence": round(self.confidence, 3),
            "latencyMs": round(self.latency_ms, 1),
            "cost": round(self.cost, 4),
            "composite": round(self.composite, 3),
        }


@dataclass
class EvolutionTrial:
    """A single evolution trial — before and after comparison."""

    trial_id: str = field(default_factory=lambda: f"evo_{uuid4().hex[:8]}")
    mutation_type: MutationType = MutationType.PROMPT_STRATEGY
    target: str = ""  # What was mutated (e.g., "system_prompt", "router_config")
    original_value: Any = None
    mutated_value: Any = None
    original_score: EvolutionScore | None = None
    mutated_score: EvolutionScore | None = None
    improved: bool = False
    timestamp: float = 0.0
    task_context: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "trialId": self.trial_id,
            "mutationType": self.mutation_type.value,
            "target": self.target,
            "originalScore": self.original_score.to_dict() if self.original_score else None,
            "mutatedScore": self.mutated_score.to_dict() if self.mutated_score else None,
            "improved": self.improved,
            "improvementDelta": round(
                (self.mutated_score.composite - self.original_score.composite) * 100, 1
            ) if self.original_score and self.mutated_score else 0.0,
            "timestamp": self.timestamp,
        }


class EvolutionEngine:
    """
    Self-improvement through continuous mutation, scoring, and reinforcement.

    The engine:
      - Proposes mutations when performance is below threshold
      - Scores both original and mutated versions
      - Reinforces mutations that improve scores
      - Rolls back mutations that degrade performance
      - Learns which mutation types work best for each target
    """

    _instance: EvolutionEngine | None = None

    def __init__(self):
        self._trials: list[EvolutionTrial] = []
        self._max_trials = 500
        self._mutation_history: dict[str, list[bool]] = {}  # target → [improved flags]
        self._mutation_success_rates: dict[str, float] = {}  # target → success rate
        self._auto_mutate_threshold = 0.7  # composite score threshold for auto-mutation

    @classmethod
    def initialize(cls) -> EvolutionEngine:
        cls._instance = cls()
        return cls._instance

    @classmethod
    def get(cls) -> EvolutionEngine:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    # ─── Mutation Proposals ───────────────────────────────────────────────────

    def propose_mutation(
        self,
        mutation_type: MutationType,
        target: str,
        current_value: Any,
    ) -> Any:
        """
        Propose a mutation for a given target.

        Uses learned mutation strategies based on past success rates.
        """
        # Learn from past mutations on this target
        history = self._mutation_history.get(target, [])
        success_rate = self._mutation_success_rates.get(target, 0.5)

        if mutation_type == MutationType.PROMPT_STRATEGY:
            return self._mutate_prompt(current_value, success_rate)
        elif mutation_type == MutationType.ROUTING_DECISION:
            return self._mutate_routing(current_value, success_rate)
        elif mutation_type == MutationType.WORKFLOW_PATTERN:
            return self._mutate_workflow(current_value, success_rate)
        elif mutation_type == MutationType.AGENT_CONFIG:
            return self._mutate_config(current_value, success_rate)
        elif mutation_type == MutationType.MODEL_SELECTION:
            return self._mutate_model(current_value, success_rate)
        elif mutation_type == MutationType.THRESHOLD_TUNING:
            return self._mutate_threshold(current_value, success_rate)
        elif mutation_type == MutationType.PARALLELIZATION:
            return self._mutate_parallelization(current_value, success_rate)
        return current_value

    def _mutate_prompt(self, current: str, success_rate: float) -> str:
        """Mutate a system prompt or instruction."""
        mutations = [
            current + "\nBe thorough and cover edge cases.",
            current + "\nProvide step-by-step reasoning.",
            current + "\nIf unsure, acknowledge uncertainty.",
            current + "\nFocus on clarity and actionable output.",
            current + "\nUse examples when helpful.",
            current.replace("Be concise.", "Be thorough."),
        ]
        # Higher success rate = more aggressive mutation
        if success_rate > 0.7:
            return random.choice(mutations)
        else:
            return mutations[0]

    def _mutate_routing(self, current: dict, success_rate: float) -> dict:
        """Mutate routing configuration."""
        mutated = dict(current) if isinstance(current, dict) else {}
        # Adjust confidence thresholds
        if "min_confidence" in mutated:
            delta = random.uniform(-0.1, 0.1)
            mutated["min_confidence"] = max(0.3, min(0.95, mutated["min_confidence"] + delta))
        # Adjust fallback behavior
        if "max_retries" in mutated:
            delta = random.choice([-1, 1])
            mutated["max_retries"] = max(0, min(3, mutated["max_retries"] + delta))
        return mutated

    def _mutate_workflow(self, current: dict, success_rate: float) -> dict:
        """Mutate workflow configuration."""
        mutated = dict(current) if isinstance(current, dict) else {}
        if "parallel_groups" in mutated:
            delta = random.choice([-1, 1])
            mutated["parallel_groups"] = max(1, mutated["parallel_groups"] + delta)
        if "max_retries" in mutated:
            mutated["max_retries"] = mutated.get("max_retries", 0) + 1
        return mutated

    def _mutate_config(self, current: dict, success_rate: float) -> dict:
        """Mutate agent configuration."""
        mutated = dict(current) if isinstance(current, dict) else {}
        for key in ["min_agents", "max_agents", "priority", "max_concurrent_tasks"]:
            if key in mutated:
                delta = random.choice([-1, 1])
                mutated[key] = max(1, mutated.get(key, 1) + delta)
        return mutated

    def _mutate_model(self, current: str, success_rate: float) -> str:
        """Mutate model selection."""
        models = ["fast", "smart", "deep", "coding"]
        if current in models:
            remaining = [m for m in models if m != current]
            return random.choice(remaining)
        return "smart"

    def _mutate_threshold(self, current: float, success_rate: float) -> float:
        """Tune a numerical threshold."""
        delta = random.uniform(-0.15, 0.15)
        return max(0.1, min(0.95, current + delta))

    def _mutate_parallelization(self, current: bool, success_rate: float) -> bool:
        """Toggle parallelization."""
        return not current

    # ─── Trial Execution ──────────────────────────────────────────────────────

    def run_trial(
        self,
        mutation_type: MutationType,
        target: str,
        original_value: Any,
        mutated_value: Any,
        original_score: EvolutionScore,
        mutated_score: EvolutionScore,
        task_context: str = "",
    ) -> EvolutionTrial:
        """
        Run a complete evolution trial, comparing original vs mutated.
        """
        trial = EvolutionTrial(
            mutation_type=mutation_type,
            target=target,
            original_value=original_value,
            mutated_value=mutated_value,
            original_score=original_score,
            mutated_score=mutated_score,
            improved=mutated_score.composite > original_score.composite,
            timestamp=time.time(),
            task_context=task_context[:200],
        )

        self._trials.append(trial)
        if len(self._trials) > self._max_trials:
            self._trials = self._trials[-self._max_trials:]

        # Update mutation history
        self._mutation_history.setdefault(target, []).append(trial.improved)
        history = self._mutation_history[target]
        if len(history) > 20:
            history = history[-20:]
        self._mutation_success_rates[target] = sum(history) / max(len(history), 1)

        return trial

    def should_mutate(self, current_score: float) -> bool:
        """Decide if a mutation should be attempted based on current score."""
        return current_score < self._auto_mutate_threshold

    # ─── Analysis ─────────────────────────────────────────────────────────────

    def get_best_mutation_type(self, target: str) -> MutationType | None:
        """Find which mutation type has worked best for a target."""
        trials = [t for t in self._trials if t.target == target and t.mutation_type]
        if not trials:
            return None

        type_scores: dict[str, float] = {}
        type_counts: dict[str, int] = {}

        for t in trials:
            key = t.mutation_type.value
            delta = (t.mutated_score.composite - t.original_score.composite) if t.original_score and t.mutated_score else 0
            type_scores[key] = type_scores.get(key, 0) + delta
            type_counts[key] = type_counts.get(key, 0) + 1

        best_type = max(type_scores, key=lambda k: type_scores[k] / max(type_counts[k], 1))
        return MutationType(best_type)

    def get_trials(self, limit: int = 50) -> list[dict]:
        return [t.to_dict() for t in self._trials[-limit:]]

    def get_status(self) -> dict[str, Any]:
        total = len(self._trials)
        improved = sum(1 for t in self._trials if t.improved)
        return {
            "totalTrials": total,
            "improvedTrials": improved,
            "improvementRate": round(improved / max(total, 1), 3),
            "targetsTracked": len(self._mutation_history),
            "mutationSuccessRates": {
                target: round(rate, 3)
                for target, rate in self._mutation_success_rates.items()
            },
            "autoMutateThreshold": self._auto_mutate_threshold,
        }

    def get_best_practices(self, limit: int = 5) -> list[dict]:
        """Get the most successful mutations as best practices."""
        successful = [t for t in self._trials if t.improved and t.original_score and t.mutated_score]
        successful.sort(
            key=lambda t: (t.mutated_score.composite - t.original_score.composite),
            reverse=True,
        )

        return [
            {
                "trialId": t.trial_id,
                "mutationType": t.mutation_type.value,
                "target": t.target,
                "improvementDelta": round(
                    (t.mutated_score.composite - t.original_score.composite) * 100, 1
                ),
                "originalComposite": round(t.original_score.composite, 3),
                "mutatedComposite": round(t.mutated_score.composite, 3),
            }
            for t in successful[:limit]
        ]

    def reset(self) -> None:
        """Reset the evolution engine (for testing)."""
        self._trials.clear()
        self._mutation_history.clear()
        self._mutation_success_rates.clear()
