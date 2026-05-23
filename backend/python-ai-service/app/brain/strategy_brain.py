"""
Strategy Brain — turns goals into tactical execution plans.

Responsibilities:
  - Task graph generation with dependency mapping
  - Optimization of execution order
  - Parallelization detection
  - Model/tool selection for each step
  - Execution routing with cost/cycle estimates
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from typing import Any

from app.brain.smart_router import SmartRouter, TaskComplexity, TaskType
from app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class StrategyStep:
    """A single step in an execution strategy."""

    id: str
    description: str
    agent_type: str = "llm"  # "llm", "sector_brain", "tool", "code"
    sector_brain_id: str | None = None
    model_mode: str = "fast"
    parallel_group: str | None = None  # Steps in same group can run in parallel
    depends_on: list[str] = field(default_factory=list)  # Step IDs this depends on
    estimated_cost: float = 0.0
    estimated_latency_ms: float = 0.0
    max_retries: int = 0
    timeout_s: int = 30
    is_critical: bool = False
    context_hint: str = ""


@dataclass
class TaskGraph:
    """Full task graph with dependencies and parallelization groups."""

    goal: str
    steps: list[StrategyStep]
    parallel_groups: int = 1  # How many groups can run in parallel
    estimated_total_cost: float = 0.0
    estimated_total_latency_ms: float = 0.0
    complexity: str = "moderate"
    confidence: float = 0.85


class StrategyBrain:
    """
    Transforms goals into structured execution strategies
    with dependency-aware task graphs.
    """

    _instance: StrategyBrain | None = None

    def __init__(self):
        self._smart_router = SmartRouter.get()

    @classmethod
    def initialize(cls) -> StrategyBrain:
        cls._instance = cls()
        return cls._instance

    @classmethod
    def get(cls) -> StrategyBrain:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    async def generate_plan(
        self,
        goal: str,
        context: str = "",
        available_brains: list[dict] | None = None,
        max_steps: int = 12,
    ) -> TaskGraph:
        """
        Generate a complete task graph from a goal.

        Uses the LLM to decompose the goal into dependency-aware steps,
        then applies the Smart Router to optimize each step.
        """
        brain_list = available_brains or []

        # First, analyze the task with the smart router
        routing = self._smart_router.analyze_task(
            task=goal,
            task_type="planning",
        )

        # Try to use LLM for plan generation
        try:
            plan_data = await self._llm_generate_plan(goal, context, brain_list, max_steps)
            steps_data = plan_data.get("steps", [])
        except Exception as exc:
            logger.warning("strategy_llm_gen_failed", error=str(exc))
            steps_data = self._fallback_plan(goal)

        # Build strategy steps with routing optimization
        steps: list[StrategyStep] = []
        parallel_groups: set[str] = set()

        for i, s in enumerate(steps_data):
            step_id = s.get("id", f"step_{i}")
            desc = s.get("description", s.get("instruction", ""))
            agent = s.get("agent_type", "llm")
            brain_id = s.get("sector_brain_id")
            deps = s.get("depends_on", [])
            pg = s.get("parallel_group")

            # Optimize model selection per step
            if agent == "llm" or agent == "sector_brain":
                step_routing = self._smart_router.analyze_task(
                    task=desc,
                    task_type=s.get("task_type", "general"),
                )
                model_mode = step_routing["recommendedMode"]
            else:
                model_mode = "fast"

            # Estimate cost and latency
            est_cost = self._estimate_cost(model_mode, len(desc))
            est_latency = self._estimate_latency(model_mode, agent)

            step = StrategyStep(
                id=step_id,
                description=desc,
                agent_type=agent,
                sector_brain_id=brain_id,
                model_mode=model_mode,
                parallel_group=pg,
                depends_on=deps,
                estimated_cost=est_cost,
                estimated_latency_ms=est_latency,
                max_retries=s.get("max_retries", 0),
                timeout_s=s.get("timeout_s", 30),
                is_critical=s.get("is_critical", False),
                context_hint=s.get("context_hint", ""),
            )
            steps.append(step)
            if pg:
                parallel_groups.add(pg)

        num_groups = max(len(parallel_groups), 1)
        total_cost = sum(s.estimated_cost for s in steps)
        total_latency = self._estimate_total_latency(steps)

        return TaskGraph(
            goal=goal,
            steps=steps,
            parallel_groups=num_groups,
            estimated_total_cost=round(total_cost, 4),
            estimated_total_latency_ms=round(total_latency, 1),
            complexity=routing["complexity"],
            confidence=routing["confidence"],
        )

    async def _llm_generate_plan(
        self,
        goal: str,
        context: str,
        brains: list[dict],
        max_steps: int,
    ) -> dict:
        """Use the LLM to generate a structured plan."""
        from app.providers.router import ProviderRouter

        pr = ProviderRouter.get()
        provider = pr.get_active_provider()
        if provider is None:
            return {"steps": self._fallback_plan(goal)}

        brain_names = [b.get("name", b.get("id", "")) for b in brains[:10]]
        brain_list_str = ", ".join(brain_names) if brain_names else "none (use default LLM)"

        system_prompt = (
            "You are JARVIS's Strategy Brain. Decompose the user's goal into a structured execution plan.\n\n"
            "Output ONLY valid JSON with this schema:\n"
            "{\n"
            '  "steps": [\n'
            "    {\n"
            '      "id": "step_0",\n'
            '      "description": "What this step does",\n'
            '      "agent_type": "llm" | "sector_brain" | "tool",\n'
            '      "sector_brain_id": "coding" | "research" | null,\n'
            '      "task_type": "code" | "research" | "analysis" | "planning" | "creative" | "general",\n'
            '      "depends_on": ["step_0"],  // step IDs this depends on\n'
            '      "parallel_group": "group_a" | null,  // same group = can parallelize\n'
            '      "is_critical": false,\n'
            '      "context_hint": "what context to pass to this step"\n'
            "    }\n"
            "  ]\n"
            "}\n\n"
            f"Available sector brains: {brain_list_str}\n"
            f"Max steps: {max_steps}\n"
            "Rules:\n"
            "- Use parallel_group for independent steps that can run simultaneously\n"
            "- Use depends_on to express ordering constraints\n"
            "- Use sector_brain_id for specialized tasks (coding, research, security, etc.)\n"
            "- No markdown, no explanation — JSON only."
        )

        user_prompt = (
            f"Goal: {goal}\n"
            f"Context: {context[:600] if context else 'None'}\n\n"
            "Generate the plan:"
        )

        result = await provider.chat(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            model_id="",
            max_tokens=2048,
        )

        raw = result.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1].lstrip("json").strip()
            if "```" in raw:
                raw = raw[: raw.index("```")]
        return json.loads(raw)

    def _fallback_plan(self, goal: str) -> list[dict]:
        """Generate a simple fallback plan when LLM is unavailable."""
        return [
            {
                "id": "step_0",
                "description": f"Analyze and understand: {goal[:100]}",
                "agent_type": "llm",
                "sector_brain_id": None,
                "task_type": "planning",
                "depends_on": [],
                "parallel_group": None,
                "is_critical": True,
            },
            {
                "id": "step_1",
                "description": f"Execute primary solution for: {goal[:100]}",
                "agent_type": "llm",
                "sector_brain_id": None,
                "task_type": "general",
                "depends_on": ["step_0"],
                "parallel_group": None,
                "is_critical": False,
            },
            {
                "id": "step_2",
                "description": "Validate results and provide summary",
                "agent_type": "llm",
                "sector_brain_id": None,
                "task_type": "analysis",
                "depends_on": ["step_1"],
                "parallel_group": None,
                "is_critical": False,
            },
        ]

    def _estimate_cost(self, model_mode: str, task_length: int) -> float:
        """Estimate cost per step based on model mode and task length."""
        from app.brain.smart_router import MODEL_COST_ESTIMATES

        cost_per_1k = MODEL_COST_ESTIMATES.get(model_mode, 0.00015)
        estimated_tokens = task_length * 1.5 + 200  # rough estimate
        return cost_per_1k * (estimated_tokens / 1000)

    def _estimate_latency(self, model_mode: str, agent_type: str) -> float:
        """Estimate latency in ms based on model mode and agent type."""
        if agent_type == "tool":
            return 500.0
        latencies = {"fast": 1000, "smart": 3000, "deep": 8000, "coding": 2000}
        return latencies.get(model_mode, 2000)

    def _estimate_total_latency(self, steps: list[StrategyStep]) -> float:
        """Estimate total wall-clock time considering parallelization."""
        # Group by parallel_group
        groups: dict[str, list[StrategyStep]] = {}
        no_group: list[StrategyStep] = []

        for step in steps:
            if step.parallel_group:
                groups.setdefault(step.parallel_group, []).append(step)
            else:
                no_group.append(step)

        # Sequential steps sum
        sequential_latency = sum(s.estimated_latency_ms for s in no_group)

        # Parallel groups: take the max latency within each group
        parallel_latency = 0.0
        for group_steps in groups.values():
            max_in_group = max(s.estimated_latency_ms for s in group_steps)
            parallel_latency += max_in_group

        return sequential_latency + parallel_latency

    def to_dict(self, graph: TaskGraph) -> dict[str, Any]:
        return {
            "goal": graph.goal,
            "steps": [
                {
                    "id": s.id,
                    "description": s.description,
                    "agentType": s.agent_type,
                    "sectorBrainId": s.sector_brain_id,
                    "modelMode": s.model_mode,
                    "parallelGroup": s.parallel_group,
                    "dependsOn": s.depends_on,
                    "estimatedCost": s.estimated_cost,
                    "estimatedLatencyMs": s.estimated_latency_ms,
                    "isCritical": s.is_critical,
                }
                for s in graph.steps
            ],
            "estimatedTotalCost": graph.estimated_total_cost,
            "estimatedTotalLatencyMs": graph.estimated_total_latency_ms,
            "parallelGroups": graph.parallel_groups,
            "complexity": graph.complexity,
            "confidence": graph.confidence,
        }
