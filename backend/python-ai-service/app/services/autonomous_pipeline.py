"""
Autonomous Task Execution Pipeline

Full autonomous execution cycle:
  1. PLAN      — Generate task graph via Strategy Brain
  2. EXECUTE   — Run each step through appropriate sector brains
  3. VALIDATE  — Check output quality and correctness
  4. DEBUG     — If validation fails, diagnose and fix
  5. RETRY     — Re-execute failed steps with fixes
  6. OPTIMIZE  — Record successful patterns for future use

This pipeline runs without excessive user interaction,
reporting progress at each stage.
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4

from app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class PipelineStage:
    """A single stage in the autonomous pipeline."""

    name: str
    status: str = "pending"  # pending, running, success, failed, skipped
    started_at: float = 0.0
    completed_at: float = 0.0
    output: str = ""
    error: str | None = None
    retries: int = 0
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class PipelineRun:
    """Complete record of an autonomous pipeline execution."""

    run_id: str = ""
    goal: str = ""
    stages: dict[str, PipelineStage] = field(default_factory=dict)
    status: str = "pending"
    started_at: float = 0.0
    completed_at: float = 0.0
    total_retries: int = 0
    max_retries_per_step: int = 2
    auto_fix: bool = True


class AutonomousPipeline:
    """
    Fully autonomous task execution pipeline.

    Usage:
        pipeline = AutonomousPipeline.get()
        result = await pipeline.run("Build a REST API for user management")
    """

    _instance: AutonomousPipeline | None = None

    def __init__(self):
        self._runs: dict[str, PipelineRun] = {}
        self._max_runs = 50

    @classmethod
    def initialize(cls) -> AutonomousPipeline:
        cls._instance = cls()
        return cls._instance

    @classmethod
    def get(cls) -> AutonomousPipeline:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    async def run(
        self,
        goal: str,
        context: str = "",
        task_type: str = "general",
        max_retries: int = 2,
        auto_fix: bool = True,
    ) -> dict[str, Any]:
        """
        Execute the full autonomous pipeline for a goal.

        Returns a comprehensive result with all stage outputs.
        """
        run_id = f"run_{uuid4().hex[:10]}"
        pipeline_run = PipelineRun(
            run_id=run_id,
            goal=goal[:200],
            started_at=time.time(),
            max_retries_per_step=max_retries,
            auto_fix=auto_fix,
        )
        pipeline_run.stages = {
            "plan": PipelineStage(name="Plan"),
            "execute": PipelineStage(name="Execute"),
            "validate": PipelineStage(name="Validate"),
            "debug": PipelineStage(name="Debug"),
            "retry": PipelineStage(name="Retry"),
            "optimize": PipelineStage(name="Optimize"),
        }

        try:
            # ── STAGE 1: PLAN ─────────────────────────────────────────────────
            await self._update_stage(pipeline_run, "plan", "running")
            plan = await self._stage_plan(goal, context, task_type)
            pipeline_run.stages["plan"].output = json.dumps(plan.get("steps", [])[:5]) if isinstance(plan, dict) else str(plan)[:500]
            pipeline_run.stages["plan"].details = plan if isinstance(plan, dict) else {}
            await self._update_stage(pipeline_run, "plan", "success")

            # ── STAGE 2: EXECUTE ──────────────────────────────────────────────
            await self._update_stage(pipeline_run, "execute", "running")
            execution_result = await self._stage_execute(goal, context, task_type)
            pipeline_run.stages["execute"].output = execution_result.get("output", "")[:1000]
            pipeline_run.stages["execute"].details = execution_result
            exec_success = execution_result.get("success", False)

            if exec_success:
                await self._update_stage(pipeline_run, "execute", "success")
            else:
                pipeline_run.stages["execute"].error = execution_result.get("error", "Execution failed")
                await self._update_stage(pipeline_run, "execute", "failed")

            # ── STAGE 3: VALIDATE ─────────────────────────────────────────────
            await self._update_stage(pipeline_run, "validate", "running")
            validation = await self._stage_validate(goal, execution_result)
            pipeline_run.stages["validate"].output = json.dumps(validation)[:500]
            pipeline_run.stages["validate"].details = validation
            validation_passed = validation.get("passed", not exec_success)

            if validation_passed:
                await self._update_stage(pipeline_run, "validate", "success")
            else:
                pipeline_run.stages["validate"].error = validation.get("feedback", "Validation failed")
                await self._update_stage(pipeline_run, "validate", "failed")

            # ── STAGE 4 & 5: DEBUG & RETRY (if needed) ────────────────────────
            if not validation_passed and auto_fix and pipeline_run.total_retries < max_retries:
                await self._update_stage(pipeline_run, "debug", "running")
                debug_result = await self._stage_debug(goal, execution_result, validation)
                pipeline_run.stages["debug"].output = debug_result.get("diagnosis", "")[:500]
                await self._update_stage(pipeline_run, "debug", "success")

                await self._update_stage(pipeline_run, "retry", "running")
                pipeline_run.total_retries += 1
                retry_result = await self._stage_retry(goal, context, debug_result)
                pipeline_run.stages["retry"].output = retry_result.get("output", "")[:1000]
                pipeline_run.stages["retry"].details = retry_result

                if retry_result.get("success"):
                    await self._update_stage(pipeline_run, "retry", "success")
                    execution_result = retry_result
                else:
                    pipeline_run.stages["retry"].error = retry_result.get("error", "Retry failed")
                    await self._update_stage(pipeline_run, "retry", "failed")
            else:
                await self._update_stage(pipeline_run, "debug", "skipped")
                await self._update_stage(pipeline_run, "retry", "skipped")

            # ── STAGE 6: OPTIMIZE ─────────────────────────────────────────────
            await self._update_stage(pipeline_run, "optimize", "running")
            await self._stage_optimize(goal, task_type, execution_result)
            await self._update_stage(pipeline_run, "optimize", "success")

            # Final status
            final_success = execution_result.get("success", False) or (
                pipeline_run.stages["execute"].status == "success"
            )
            pipeline_run.status = "completed" if final_success else "completed_with_issues"

        except Exception as exc:
            logger.error("pipeline_crash", run_id=run_id, error=str(exc))
            pipeline_run.status = "failed"
            # Mark any running stages as failed
            for stage in pipeline_run.stages.values():
                if stage.status == "running":
                    stage.status = "failed"
                    stage.error = str(exc)

        pipeline_run.completed_at = time.time()

        # Store in history
        self._runs[run_id] = pipeline_run
        if len(self._runs) > self._max_runs:
            # Remove oldest
            oldest_key = min(self._runs.keys(), key=lambda k: self._runs[k].started_at)
            del self._runs[oldest_key]

        # Store in evolution service
        try:
            from app.services.evolution_service import EvolutionService
            evo = EvolutionService.get()
            evo.record_execution(
                task=goal,
                task_type=task_type,
                success=pipeline_run.status == "completed",
                output=pipeline_run.stages["execute"].output[:500],
                confidence=0.85 if pipeline_run.status == "completed" else 0.3,
                latency_ms=(pipeline_run.completed_at - pipeline_run.started_at) * 1000,
                metadata={"run_id": run_id, "status": pipeline_run.status},
            )
        except Exception as exc:
            logger.debug("pipeline_evolution_store_skipped", error=str(exc))

        return self._run_to_dict(pipeline_run)

    async def _stage_plan(self, goal: str, context: str, task_type: str) -> dict:
        """PLAN stage — generate execution strategy."""
        try:
            from app.brain.strategy_brain import StrategyBrain
            from app.brain.sector_brains import list_sector_brains

            strategy = StrategyBrain.get()
            plan = await strategy.generate_plan(
                goal=goal,
                context=context,
                available_brains=list_sector_brains(),
            )
            return strategy.to_dict(plan)
        except Exception as exc:
            logger.warning("pipeline_plan_fallback", error=str(exc))
            return {"steps": [{"id": "step_0", "description": goal[:100], "agentType": "llm"}], "note": "Fallback plan"}

    async def _stage_execute(self, goal: str, context: str, task_type: str) -> dict:
        """EXECUTE stage — run the task."""
        try:
            from app.brain.macro_brain import MacroBrain
            macro = MacroBrain.get()
            result = await macro.process(task=goal, context=context, task_type=task_type)
            return result
        except Exception as exc:
            return {"success": False, "output": "", "error": str(exc), "confidence": 0.0}

    async def _stage_validate(self, goal: str, result: dict) -> dict:
        """VALIDATE stage — check output quality."""
        success = result.get("success", False)
        output = result.get("output", "")
        confidence = result.get("confidence", 0.0)

        if not success:
            return {"passed": False, "feedback": "Execution did not succeed", "score": 0.0}

        if not output:
            return {"passed": False, "feedback": "No output produced", "score": 0.0}

        if confidence < 0.3:
            return {"passed": False, "feedback": f"Confidence too low: {confidence}", "score": confidence}

        return {"passed": True, "feedback": "Validation passed", "score": confidence}

    async def _stage_debug(self, goal: str, result: dict, validation: dict) -> dict:
        """DEBUG stage — diagnose and suggest fixes."""
        error = result.get("error", validation.get("feedback", "Unknown issue"))

        try:
            from app.providers.router import ProviderRouter
            pr = ProviderRouter.get()
            provider = pr.get_active_provider()
            if provider:
                debug_result = await provider.chat(
                    messages=[{
                        "role": "user",
                        "content": (
                            f"Task: {goal}\n"
                            f"Error/Issue: {error}\n"
                            "Diagnose the problem and suggest a specific fix. "
                            "Be concise."
                        ),
                    }],
                    model_id="",
                    max_tokens=512,
                )
                diagnosis = debug_result.get("choices", [{}])[0].get("message", {}).get("content", "")
                return {"diagnosis": diagnosis, "fix_suggested": True}
        except Exception:
            pass

        return {"diagnosis": f"Attempt to fix: {error}", "fix_suggested": True}

    async def _stage_retry(self, goal: str, context: str, debug_result: dict) -> dict:
        """RETRY stage — re-execute with debug fixes."""
        try:
            from app.brain.macro_brain import MacroBrain
            macro = MacroBrain.get()

            # Include debug diagnosis in context for better results
            enriched_context = f"{context}\n\nDebug diagnosis: {debug_result.get('diagnosis', '')}"

            result = await macro.process(
                task=goal,
                context=enriched_context,
                task_type="general",
            )
            return result
        except Exception as exc:
            return {"success": False, "output": "", "error": str(exc), "confidence": 0.0}

    async def _stage_optimize(self, goal: str, task_type: str, result: dict) -> None:
        """OPTIMIZE stage — record successful patterns."""
        try:
            from app.services.evolution_service import EvolutionService
            evo = EvolutionService.get()
            evo.record_execution(
                task=goal,
                task_type=task_type,
                success=result.get("success", False),
                output=result.get("output", ""),
                confidence=result.get("confidence", 0.5),
                metadata={"source": "autonomous_pipeline"},
            )
        except Exception:
            pass

    async def _update_stage(self, run: PipelineRun, stage_name: str, status: str) -> None:
        """Update a stage's status and timestamps."""
        stage = run.stages.get(stage_name)
        if stage is None:
            return
        stage.status = status
        if status == "running":
            stage.started_at = time.time()
        elif status in ("success", "failed", "skipped"):
            stage.completed_at = time.time()

    def _run_to_dict(self, run: PipelineRun) -> dict[str, Any]:
        """Convert a pipeline run to a serializable dict."""
        total_duration = round((run.completed_at - run.started_at) * 1000, 1) if run.completed_at else 0.0

        return {
            "runId": run.run_id,
            "goal": run.goal,
            "status": run.status,
            "totalRetries": run.total_retries,
            "durationMs": total_duration,
            "stages": {
                name: {
                    "name": s.name,
                    "status": s.status,
                    "output": s.output[:500] if s.output else "",
                    "error": s.error,
                    "retries": s.retries,
                    "durationMs": round((s.completed_at - s.started_at) * 1000, 1) if s.completed_at and s.started_at else 0.0,
                }
                for name, s in run.stages.items()
            },
            "success": run.status == "completed",
        }

    def get_run(self, run_id: str) -> dict | None:
        run = self._runs.get(run_id)
        return self._run_to_dict(run) if run else None

    def get_runs(self, limit: int = 10) -> list[dict]:
        sorted_runs = sorted(self._runs.values(), key=lambda r: r.started_at, reverse=True)
        return [self._run_to_dict(r) for r in sorted_runs[:limit]]

    def get_status(self) -> dict[str, Any]:
        total = len(self._runs)
        completed = sum(1 for r in self._runs.values() if r.status == "completed")
        failed = sum(1 for r in self._runs.values() if r.status in ("failed", "completed_with_issues"))
        return {
            "totalRuns": total,
            "completedRuns": completed,
            "failedRuns": failed,
            "successRate": round(completed / max(total, 1), 3),
            "maxRetriesPerStep": 2,
            "autoFix": True,
        }
