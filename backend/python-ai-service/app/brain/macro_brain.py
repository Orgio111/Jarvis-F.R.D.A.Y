"""
Macro Brain — JARVIS's central consciousness and strategic intelligence.

Acts as the CEO of the cognitive architecture:
  - Receives high-level goals from the user
  - Analyzes tasks and routes them to appropriate Sector Brains
  - Uses the Strategy Brain for complex multi-step planning
  - Uses the Smart Router for model selection optimization
  - Tracks agent performance via the Agent Reputation system
  - Aggregates results from multiple brains into coherent responses
  - Maintains system-wide optimization and memory prioritization
"""
from __future__ import annotations

import time
from typing import Any

from app.brain.smart_router import SmartRouter, TaskComplexity, TaskType
from app.brain.strategy_brain import StrategyBrain, TaskGraph
from app.brain.agent_reputation import AgentReputation
from app.brain.sector_brains import (
    BaseSectorBrain,
    SectorBrainResult,
    SECTOR_BRAIN_REGISTRY,
    list_sector_brains,
)
from app.core.logging import get_logger

logger = get_logger(__name__)


class MacroBrain:
    """
    Central orchestrator — the primary entry point for all cognitive operations.

    Default routing logic:
      1. Analyze task via SmartRouter
      2. For complex tasks → StrategyBrain for task graph
      3. Route sub-tasks to appropriate SectorBrains
      4. For simple tasks → direct LLM call
      5. Track everything via AgentReputation
    """

    _instance: MacroBrain | None = None

    def __init__(self):
        self._smart_router = SmartRouter.get()
        self._strategy_brain = StrategyBrain.get()
        self._reputation = AgentReputation.get()
        self._brain_instances: dict[str, BaseSectorBrain] = {}

    @classmethod
    def initialize(cls) -> MacroBrain:
        cls._instance = cls()
        return cls._instance

    @classmethod
    def get(cls) -> MacroBrain:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def get_brain(self, sector_id: str) -> BaseSectorBrain | None:
        """Get or create a sector brain instance."""
        if sector_id not in self._brain_instances:
            brain_class = SECTOR_BRAIN_REGISTRY.get(sector_id)
            if brain_class is None:
                return None
            self._brain_instances[sector_id] = brain_class()
        return self._brain_instances[sector_id]

    async def process(
        self,
        task: str,
        context: str = "",
        task_type: str = "general",
        preferred_mode: str | None = None,
        sector_brain_id: str | None = None,
        max_tokens: int = 2048,
    ) -> dict[str, Any]:
        """
        Main entry point for processing a task through the cognitive architecture.

        Returns a comprehensive result with routing decisions, execution results,
        and performance metrics.
        """
        start = time.perf_counter()

        # 1. Analyze via Smart Router
        routing = self._smart_router.analyze_task(
            task=task,
            task_type=task_type,
            user_preferred_mode=preferred_mode,
        )

        result: dict[str, Any] = {
            "task": task[:200],
            "taskType": task_type,
            "routing": routing,
            "success": False,
            "output": "",
            "confidence": 0.0,
            "elapsedMs": 0.0,
            "brainResults": [],
            "error": None,
        }

        # 2. If specific sector brain requested, route directly
        if sector_brain_id:
            brain = self.get_brain(sector_brain_id)
            if brain:
                brain_result = await brain.process(task, context, max_tokens)
                result["brainResults"].append({
                    "sector": sector_brain_id,
                    "result": self._brain_result_to_dict(brain_result),
                })
                result["output"] = brain_result.output
                result["success"] = brain_result.success
                result["confidence"] = brain_result.confidence
                result["error"] = brain_result.error

                # Track reputation
                self._reputation.record(
                    agent_id=f"sector_{sector_brain_id}",
                    success=brain_result.success,
                    confidence=brain_result.confidence,
                    latency_ms=brain_result.elapsed_ms,
                    task_type=task_type,
                    agent_type="sector_brain",
                )

                elapsed = round((time.perf_counter() - start) * 1000, 1)
                result["elapsedMs"] = elapsed
                return result

        # 3. For complex tasks, use Strategy Brain for decomposition
        if routing["complexity"] in ("complex", "critical") or preferred_mode == "deep":
            try:
                plan = await self._strategy_brain.generate_plan(
                    goal=task,
                    context=context,
                    available_brains=list_sector_brains(),
                )
                result["plan"] = self._strategy_brain.to_dict(plan)

                # Execute each step
                step_results = await self._execute_plan(plan, context)
                result["brainResults"] = step_results

                # Aggregate results
                outputs = [sr.get("result", {}).get("output", "") for sr in step_results if sr.get("result", {}).get("success")]
                result["output"] = "\n\n".join(o for o in outputs if o) or "Plan executed — see step results."
                result["success"] = all(sr.get("result", {}).get("success", False) for sr in step_results if sr.get("is_critical", False))
                result["confidence"] = sum(sr.get("result", {}).get("confidence", 0.0) for sr in step_results) / max(len(step_results), 1)

            except Exception as exc:
                logger.warning("macro_brain_plan_execution_failed", error=str(exc))
                # Fall through to direct LLM
                result["error"] = f"Plan execution failed: {exc}"
                direct = await self._direct_llm(task, context, max_tokens)
                result["output"] = direct.get("output", "")
                result["success"] = direct.get("success", False)
                result["confidence"] = direct.get("confidence", 0.0)
                result["error"] = direct.get("error")

        # 4. For simpler tasks, use direct LLM or appropriate sector brain
        else:
            # Try to route to the best sector brain
            best_brain_id = routing.get("suggestedAgents", [None])[0]
            if best_brain_id and best_brain_id in SECTOR_BRAIN_REGISTRY:
                brain = self.get_brain(best_brain_id)
                if brain:
                    brain_result = await brain.process(task, context, max_tokens)
                    result["brainResults"].append({
                        "sector": best_brain_id,
                        "result": self._brain_result_to_dict(brain_result),
                    })
                    result["output"] = brain_result.output
                    result["success"] = brain_result.success
                    result["confidence"] = brain_result.confidence
                    result["error"] = brain_result.error

                    self._reputation.record(
                        agent_id=f"sector_{best_brain_id}",
                        success=brain_result.success,
                        confidence=brain_result.confidence,
                        latency_ms=brain_result.elapsed_ms,
                        task_type=task_type,
                        agent_type="sector_brain",
                    )
                else:
                    direct = await self._direct_llm(task, context, max_tokens)
                    result["output"] = direct.get("output", "")
                    result["success"] = direct.get("success", False)
                    result["confidence"] = direct.get("confidence", 0.0)
                    result["error"] = direct.get("error")
            else:
                direct = await self._direct_llm(task, context, max_tokens)
                result["output"] = direct.get("output", "")
                result["success"] = direct.get("success", False)
                result["confidence"] = direct.get("confidence", 0.0)
                result["error"] = direct.get("error")

        elapsed = round((time.perf_counter() - start) * 1000, 1)
        result["elapsedMs"] = elapsed

        # Track overall reputation
        self._reputation.record(
            agent_id="macro_brain",
            success=result["success"],
            confidence=result["confidence"],
            latency_ms=elapsed,
            task_type=task_type,
            agent_type="brain",
        )

        return result

    async def _direct_llm(
        self,
        task: str,
        context: str,
        max_tokens: int,
    ) -> dict[str, Any]:
        """Fallback: direct LLM call without sector brains."""
        try:
            from app.providers.router import ProviderRouter

            pr = ProviderRouter.get()
            provider = pr.get_active_provider()
            if provider is None:
                return {"success": False, "output": "", "confidence": 0.0, "error": "No provider available"}

            system = (
                "You are JARVIS — an advanced AI assistant. "
                "Respond directly to the user's request with clear, actionable output."
            )
            user = f"Task: {task}\n\nContext: {context[:1000] if context else 'None'}"

            result = await provider.chat(
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                model_id="",
                max_tokens=max_tokens,
            )

            content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
            return {"success": True, "output": content, "confidence": 0.8, "error": None}

        except Exception as exc:
            return {"success": False, "output": "", "confidence": 0.0, "error": str(exc)}

    async def _execute_plan(
        self,
        plan: TaskGraph,
        context: str,
    ) -> list[dict]:
        """Execute all steps in a task graph, respecting dependencies."""
        executed: dict[str, dict] = {}
        results: list[dict] = []

        # Sort steps by dependency order (topological sort is ideal, but simple pass is fine)
        remaining = list(plan.steps)
        max_passes = 50
        passes = 0

        while remaining and passes < max_passes:
            passes += 1
            batch = [
                s for s in remaining
                if all(dep in executed for dep in s.depends_on)
            ]
            if not batch:
                # Circular dependency — just execute remaining
                batch = remaining[:]
                remaining = []

            for step in batch:
                remaining.remove(step)
                step_result = await self._execute_step(step, context, executed)
                executed[step.id] = step_result
                results.append(step_result)

        return results

    async def _execute_step(
        self,
        step: Any,
        context: str,
        executed: dict[str, dict],
    ) -> dict:
        """Execute a single strategy step."""
        step_start = time.perf_counter()

        # Gather context from dependencies
        dep_context = ""
        for dep_id in step.depends_on:
            dep_result = executed.get(dep_id, {})
            dep_output = dep_result.get("result", {}).get("output", "")
            if dep_output:
                dep_context += f"\n[{dep_id}]: {dep_output[:200]}"

        full_context = f"{context}\n{dep_context}".strip()
        full_context = full_context[:2000]

        result: dict = {
            "stepId": step.id,
            "description": step.description,
            "agentType": step.agent_type,
            "isCritical": step.is_critical,
            "success": False,
            "result": {},
        }

        try:
            if step.agent_type == "sector_brain" and step.sector_brain_id:
                brain = self.get_brain(step.sector_brain_id)
                if brain:
                    brain_result = await brain.process(
                        task=step.description,
                        context=full_context,
                    )
                    result["result"] = self._brain_result_to_dict(brain_result)
                    result["success"] = brain_result.success

                    self._reputation.record(
                        agent_id=f"sector_{step.sector_brain_id}",
                        success=brain_result.success,
                        confidence=brain_result.confidence,
                        latency_ms=brain_result.elapsed_ms,
                        task_type=step.sector_brain_id,
                        agent_type="sector_brain",
                    )
                else:
                    # Fallback to LLM
                    llm_result = await self._direct_llm(step.description, full_context, 1024)
                    result["result"] = llm_result
                    result["success"] = llm_result.get("success", False)

            elif step.agent_type == "tool":
                # Tool execution — currently a placeholder
                result["result"] = {"output": f"[Tool step: {step.description}]", "success": True}
                result["success"] = True

            else:  # llm or default
                llm_result = await self._direct_llm(step.description, full_context, 1024)
                result["result"] = llm_result
                result["success"] = llm_result.get("success", False)

        except Exception as exc:
            result["result"] = {"error": str(exc), "success": False}
            result["success"] = False

        elapsed = round((time.perf_counter() - step_start) * 1000, 1)
        result["result"]["elapsedMs"] = elapsed
        return result

    def _brain_result_to_dict(self, br: SectorBrainResult) -> dict:
        return {
            "success": br.success,
            "output": br.output[:1000] if br.output else "",
            "confidence": br.confidence,
            "reasoning": br.reasoning,
            "suggestions": br.suggestions[:5],
            "elapsedMs": br.elapsed_ms,
            "error": br.error,
            "brainId": br.brain_id,
            "brainName": br.brain_name,
        }

    def get_status(self) -> dict[str, Any]:
        """Return overall system status including all brain components."""
        return {
            "macroBrain": {
                "initialized": True,
                "sectorBrainCount": len(self._brain_instances),
                "availableSectors": len(SECTOR_BRAIN_REGISTRY),
            },
            "sectorBrains": list_sector_brains(),
            "reputation": {
                "trackedAgents": len(self._reputation._records) if hasattr(self._reputation, '_records') else 0,
            },
            "strategyBrain": {
                "available": True,
            },
            "smartRouter": {
                "available": True,
            },
        }
