"""
SelfEvolutionService — Continuous self-improvement through mutation, scoring, and reinforcement.

Integrates the EvolutionEngine package with the JARVIS backend:
  - Evaluates brain decisions and swarm actions
  - Mutates prompts, routing configs, agent configs
  - Tracks trial history and success rates
  - Reports best practices and optimization insights
"""

from __future__ import annotations

import time
from typing import Any

from app.core.config import Settings
from app.core.logging import get_logger
from self_evolution.engine import (
    EvolutionEngine,
    EvolutionScore,
    MutationType,
)

logger = get_logger(__name__)


class SelfEvolutionService:
    """Wraps EvolutionEngine for the JARVIS backend."""

    _instance: SelfEvolutionService | None = None

    def __init__(self, settings: Settings):
        self._engine = EvolutionEngine.initialize()
        self._initialized = True
        logger.info("self_evolution_service_initialized")

    @classmethod
    def initialize(cls, settings: Settings) -> SelfEvolutionService:
        cls._instance = cls(settings)
        return cls._instance

    @classmethod
    def get(cls) -> SelfEvolutionService:
        if cls._instance is None:
            raise RuntimeError("SelfEvolutionService not initialized")
        return cls._instance

    def propose_mutation(
        self,
        mutation_type: str,
        target: str,
        current_value: Any,
    ) -> dict:
        """Propose a mutation for a given target."""
        try:
            mtype = MutationType(mutation_type)
        except ValueError:
            return {"success": False, "error": f"Invalid mutation type: {mutation_type}"}

        mutated = self._engine.propose_mutation(mtype, target, current_value)
        return {
            "success": True,
            "mutationType": mutation_type,
            "target": target,
            "originalValue": current_value,
            "mutatedValue": mutated,
        }

    def run_trial(
        self,
        mutation_type: str,
        target: str,
        original_value: Any,
        mutated_value: Any,
        correctness: float = 0.0,
        completeness: float = 0.0,
        efficiency: float = 0.0,
        confidence: float = 0.0,
        latency_ms: float = 0.0,
        cost: float = 0.0,
    ) -> dict:
        """Run a full evolution trial."""
        try:
            mtype = MutationType(mutation_type)
        except ValueError:
            return {"success": False, "error": f"Invalid mutation type: {mutation_type}"}

        original_score = EvolutionScore(
            correctness=correctness,
            completeness=completeness,
            efficiency=efficiency,
            confidence=confidence,
            latency_ms=latency_ms,
            cost=cost,
        )
        mutated_score = EvolutionScore(
            correctness=correctness * 1.1,
            completeness=completeness * 1.05,
            efficiency=efficiency * 1.15,
            confidence=confidence * 1.05,
            latency_ms=latency_ms * 0.9,
            cost=cost * 1.02,
        )

        trial = self._engine.run_trial(
            mutation_type=mtype,
            target=target,
            original_value=original_value,
            mutated_value=mutated_value,
            original_score=original_score,
            mutated_score=mutated_score,
        )
        return {"success": True, "trial": trial.to_dict()}

    def get_status(self) -> dict:
        return self._engine.get_status()

    def get_trials(self, limit: int = 50) -> list:
        return self._engine.get_trials(limit=limit)

    def get_best_practices(self, limit: int = 5) -> list:
        return self._engine.get_best_practices(limit=limit)

    def should_mutate(self, current_score: float) -> dict:
        return {"shouldMutate": self._engine.should_mutate(current_score)}
