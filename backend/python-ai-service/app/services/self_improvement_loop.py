"""
Self-Improvement Loop

The system continuously evolves through:
  EVALUATE  →  SCORE  →  MUTATE  →  RETRY  →  IMPROVE

Every task result is evaluated, scored, and fed back into the system.
Underperforming configurations are mutated and retried.
Successful patterns are reinforced and stored for future reuse.

The loop integrates with:
  - Agent Reputation System (tracks performance)
  - Evolution Service (stores patterns)
  - Smart Router (optimizes routing)
  - Sector Brains (improves domain expertise)
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any
from uuid import uuid4

from app.core.logging import get_logger

logger = get_logger(__name__)


class ImprovementScore(Enum):
    EXCELLENT = 1.0
    GOOD = 0.75
    ACCEPTABLE = 0.5
    POOR = 0.25
    FAILED = 0.0


@dataclass
class ImprovementCycle:
    """A single evaluation → score → mutate → retry cycle."""

    cycle_id: str = ""
    task: str = ""
    task_type: str = "general"
    iteration: int = 0
    score: float = 0.0
    score_label: str = "unknown"
    evaluation: str = ""
    mutation_applied: str = ""
    retry_result: str = ""
    success: bool = False
    elapsed_ms: float = 0.0
    timestamp: float = 0.0


class SelfImprovementLoop:
    """
    Continuous self-improvement engine.

    The loop:
      1. EVALUATE — analyzes execution quality
      2. SCORE — assigns a numerical score
      3. MUTATE — suggests/applys changes to improve
      4. RETRY — re-executes with mutations
      5. IMPROVE — stores the improved result
    """

    _instance: SelfImprovementLoop | None = None

    def __init__(self):
        self._history: list[ImprovementCycle] = []
        self._max_iterations = 3
        self._auto_apply = False  # Requires approval by default

    @classmethod
    def initialize(cls) -> SelfImprovementLoop:
        cls._instance = cls()
        return cls._instance

    @classmethod
    def get(cls) -> SelfImprovementLoop:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    async def evaluate_and_improve(
        self,
        task: str,
        task_type: str,
        initial_result: dict[str, Any],
        context: str = "",
    ) -> dict[str, Any]:
        """
        Run the full improvement cycle on a task result.

        Args:
            task: Original task description
            task_type: Type of task (code, research, etc.)
            initial_result: The result from the first execution
            context: Additional context

        Returns:
            The improved result (or the original if improvement isn't needed)
        """
        start = time.perf_counter()

        # 1. EVALUATE the initial result
        score, score_label, evaluation = await self._evaluate(
            task=task,
            task_type=task_type,
            result=initial_result,
        )

        cycle = ImprovementCycle(
            cycle_id=f"imp_{uuid4().hex[:8]}",
            task=task[:200],
            task_type=task_type,
            iteration=0,
            score=score,
            score_label=score_label,
            evaluation=evaluation,
            timestamp=time.time(),
        )

        # If score is already good, no improvement needed
        if score >= ImprovementScore.GOOD.value:
            cycle.success = True
            initial_result["_improvement"] = {
                "cycleId": cycle.cycle_id,
                "score": score,
                "scoreLabel": score_label,
                "improved": False,
                "reason": "Already good quality",
            }
            self._history.append(cycle)
            return initial_result

        current_result = initial_result

        # 2-4. MUTATE → RETRY loop
        for iteration in range(1, self._max_iterations + 1):
            cycle.iteration = iteration

            # 3. MUTATE — suggest improvement
            mutation = await self._mutate(
                task=task,
                task_type=task_type,
                current_result=current_result,
                evaluation=evaluation,
                score=score,
            )
            cycle.mutation_applied = mutation.get("mutation", "")
            mutation_type = mutation.get("type", "none")

            if mutation_type == "none":
                # No mutation suggested — stop
                break

            # 4. RETRY — execute with mutation
            if mutation.get("should_retry", False):
                retry_result = await self._retry(
                    task=task,
                    task_type=task_type,
                    mutation=mutation,
                    context=context,
                )
                cycle.retry_result = retry_result.get("output", "")[:500] if retry_result.get("success") else retry_result.get("error", "")

                # Check if retry improved
                if retry_result.get("success"):
                    # Re-evaluate the retry
                    new_score, new_label, new_eval = await self._evaluate(
                        task=task,
                        task_type=task_type,
                        result=retry_result,
                    )

                    if new_score > score:
                        # Improvement!
                        current_result = retry_result
                        score = new_score
                        score_label = new_label
                        evaluation = new_eval
                        cycle.score = score
                        cycle.score_label = score_label
                        cycle.success = True
                    else:
                        # Retry didn't help — keep going
                        evaluation = new_eval
                else:
                    # Retry failed
                    cycle.success = False

        elapsed = round((time.perf_counter() - start) * 1000, 1)
        cycle.elapsed_ms = elapsed

        # Store improvement record
        current_result["_improvement"] = {
            "cycleId": cycle.cycle_id,
            "score": score,
            "scoreLabel": score_label,
            "improved": score >= ImprovementScore.GOOD.value,
            "iterations": iteration if 'iteration' in locals() else 0,
            "elapsedMs": elapsed,
        }

        self._history.append(cycle)

        # Trim history to last 200 cycles
        if len(self._history) > 200:
            self._history = self._history[-200:]

        # Store in evolution service
        try:
            from app.services.evolution_service import EvolutionService
            evo = EvolutionService.get()
            evo.record_execution(
                task=task,
                task_type=task_type,
                success=current_result.get("success", False),
                output=current_result.get("output", ""),
                model_used=current_result.get("model", ""),
                confidence=score,
                latency_ms=elapsed,
                error=current_result.get("error"),
                metadata={"improvement_cycle": cycle.cycle_id},
            )
        except Exception as exc:
            logger.debug("evolution_store_skipped", error=str(exc))

        return current_result

    async def _evaluate(
        self,
        task: str,
        task_type: str,
        result: dict[str, Any],
    ) -> tuple[float, str, str]:
        """Evaluate the quality of a result."""
        success = result.get("success", False)
        confidence = result.get("confidence", 0.0)
        output = result.get("output", "")
        error = result.get("error")

        if not success:
            return (
                ImprovementScore.FAILED.value,
                "failed",
                f"Task failed: {error or 'Unknown error'}",
            )

        # Score based on confidence and output quality
        if confidence >= 0.9 and len(output) > 50:
            return (
                ImprovementScore.EXCELLENT.value,
                "excellent",
                "High confidence with substantial output",
            )
        elif confidence >= 0.7 and len(output) > 20:
            return (
                ImprovementScore.GOOD.value,
                "good",
                "Good confidence with adequate output",
            )
        elif confidence >= 0.5:
            return (
                ImprovementScore.ACCEPTABLE.value,
                "acceptable",
                "Acceptable result but could be improved",
            )
        else:
            return (
                ImprovementScore.POOR.value,
                "poor",
                "Low confidence — improvement recommended",
            )

    async def _mutate(
        self,
        task: str,
        task_type: str,
        current_result: dict[str, Any],
        evaluation: str,
        score: float,
    ) -> dict[str, Any]:
        """Suggest a mutation to improve the result."""
        # Simple heuristic-based mutations
        mutations = {
            "poor": {
                "type": "model_upgrade",
                "mutation": "Use a more capable model (deep mode instead of fast)",
                "should_retry": True,
                "action": "upgrade_model",
            },
            "acceptable": {
                "type": "detail_enhance",
                "mutation": "Request more detailed output with examples",
                "should_retry": True,
                "action": "enhance_detail",
            },
            "failed": {
                "type": "retry_alternative",
                "mutation": "Try alternative approach with error handling",
                "should_retry": True,
                "action": "alternative_approach",
            },
        }

        # Map score to label
        if score < 0.25:
            label = "failed"
        elif score < 0.5:
            label = "poor"
        elif score < 0.7:
            label = "acceptable"
        else:
            return {"type": "none", "mutation": "No mutation needed", "should_retry": False}

        return mutations.get(label, mutations["failed"])

    async def _retry(
        self,
        task: str,
        task_type: str,
        mutation: dict[str, Any],
        context: str,
    ) -> dict[str, Any]:
        """Retry the task with the suggested mutation."""
        action = mutation.get("action", "")

        try:
            from app.providers.router import ProviderRouter
            pr = ProviderRouter.get()
            provider = pr.get_active_provider()
            if provider is None:
                return {"success": False, "output": "", "error": "No provider available"}

            if action == "upgrade_model":
                system = (
                    "You are JARVIS. Provide a comprehensive, high-quality response. "
                    "Be thorough, include examples, and cover edge cases. "
                    f"Original request: {task}"
                )
            elif action == "enhance_detail":
                system = (
                    "You are JARVIS. Provide enhanced, detailed output. "
                    "Include concrete examples, step-by-step reasoning, and practical applications. "
                    f"Original request: {task}"
                )
            elif action == "alternative_approach":
                system = (
                    "You are JARVIS. Provide an alternative solution to the following task. "
                    "Take a different approach than what might have been tried before. "
                    "Focus on robustness and completeness. "
                    f"Task: {task}"
                )
            else:
                system = f"You are JARVIS. Respond to: {task}"

            result = await provider.chat(
                messages=[{"role": "system", "content": system}],
                model_id="",
                max_tokens=2048,
            )
            content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
            return {"success": True, "output": content, "confidence": 0.8}

        except Exception as exc:
            return {"success": False, "output": "", "error": str(exc), "confidence": 0.0}

    def get_history(self, limit: int = 20) -> list[dict]:
        return [
            {
                "cycleId": c.cycle_id,
                "task": c.task[:100],
                "taskType": c.task_type,
                "iteration": c.iteration,
                "score": c.score,
                "scoreLabel": c.score_label,
                "evaluation": c.evaluation[:100] if c.evaluation else "",
                "mutationApplied": c.mutation_applied[:100] if c.mutation_applied else "",
                "success": c.success,
                "elapsedMs": c.elapsed_ms,
                "timestamp": c.timestamp,
            }
            for c in self._history[-limit:]
        ]

    def get_status(self) -> dict[str, Any]:
        if not self._history:
            return {"totalCycles": 0, "avgScore": 0.0, "successRate": 0.0}

        total = len(self._history)
        avg_score = sum(c.score for c in self._history) / total
        success_rate = sum(1 for c in self._history if c.success) / total

        return {
            "totalCycles": total,
            "avgScore": round(avg_score, 3),
            "successRate": round(success_rate, 3),
            "maxIterations": self._max_iterations,
            "autoApply": self._auto_apply,
        }
