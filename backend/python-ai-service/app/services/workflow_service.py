from __future__ import annotations

import time
import uuid
from typing import Any

from app.core.config import Settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class WorkflowService:
    """Singleton service wrapping the Ruflo workflow engine for the JARVIS backend."""

    _instance: WorkflowService | None = None

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._initialized = False
        self._orchestrator: Any = None
        self._executor: Any = None
        self._workflow_store: dict[str, dict] = {}

    @classmethod
    def initialize(cls, settings: Settings) -> WorkflowService:
        instance = cls(settings)
        cls._instance = instance
        return instance

    @classmethod
    def get(cls) -> WorkflowService:
        if cls._instance is None:
            raise RuntimeError("WorkflowService not initialized")
        return cls._instance

    async def _ensure_orchestrator(self) -> Any:
        if self._orchestrator is not None:
            return self._orchestrator

        from workflow_engine.orchestrator import TaskOrchestrator
        from workflow_engine.executor import WorkflowExecutor

        executor = WorkflowExecutor()
        self._executor = executor

        # Register built-in handlers
        self._register_builtin_handlers(executor)

        orchestrator = TaskOrchestrator(executor=executor)
        self._orchestrator = orchestrator

        logger.info("workflow_service_initialized")
        return orchestrator

    def _register_builtin_handlers(self, executor: Any) -> None:
        """Register default task handlers that workflows can reference."""

        async def echo_handler(message: str = "") -> dict:
            return {"echoed": message}

        async def delay_handler(duration_seconds: float = 1.0) -> dict:
            import asyncio
            await asyncio.sleep(duration_seconds)
            return {"delayed": duration_seconds}

        async def log_handler(message: str = "", level: str = "info") -> dict:
            log_fn = getattr(logger, level, logger.info)
            log_fn("workflow_log", message=message)
            return {"logged": True, "message": message, "level": level}

        async def combine_handler(inputs: list[dict] | None = None) -> dict:
            combined: dict[str, Any] = {}
            for item in inputs or []:
                if isinstance(item, dict):
                    combined.update(item)
            return {"combined": combined}

        executor.register_handler("echo", echo_handler)
        executor.register_handler("delay", delay_handler)
        executor.register_handler("log", log_handler)
        executor.register_handler("combine", combine_handler)

    async def create_workflow(
        self,
        name: str,
        task_specs: list[dict[str, Any]],
        description: str = "",
        context: dict[str, Any] | None = None,
    ) -> dict:
        """Create a linear pipeline workflow and store it."""
        orchestrator = await self._ensure_orchestrator()
        wf = orchestrator.build_linear_pipeline(
            workflow_id=f"wf_{uuid.uuid4().hex[:12]}",
            name=name,
            task_specs=task_specs,
            description=description,
            context=context,
        )
        wf_dict = {
            "id": wf.id,
            "name": wf.name,
            "description": wf.description,
            "version": wf.version,
            "status": wf.status.value,
            "stepCount": len(wf.steps),
            "tags": wf.tags,
            "createdAt": wf.created_at,
        }
        self._workflow_store[wf.id] = {"workflow": wf, "specs": task_specs}
        return wf_dict

    async def run_workflow(
        self,
        workflow_id: str,
        initial_context: dict[str, Any] | None = None,
    ) -> dict:
        """Execute a stored workflow."""
        orchestrator = await self._ensure_orchestrator()
        entry = self._workflow_store.get(workflow_id)
        if entry is None:
            return {"success": False, "error": f"workflow_not_found:{workflow_id}"}

        wf = entry["workflow"]
        result = await orchestrator.run_workflow(wf, initial_context)

        return {
            "success": result.status.value in ("completed",),
            "workflowId": result.workflow_id,
            "status": result.status.value,
            "totalSteps": result.total_steps,
            "completedSteps": result.completed_steps,
            "failedSteps": result.failed_steps,
            "durationMs": round(result.duration_ms, 1),
            "steps": {
                sid: {"status": step.status.value, "error": step.error}
                for sid, step in ((s.id, s) for s in wf.steps)
            },
            "context": result.context,
            "error": result.error,
        }

    async def list_workflows(self) -> list[dict]:
        return [
            {
                "id": wid,
                "name": entry["workflow"].name,
                "status": entry["workflow"].status.value,
                "stepCount": len(entry["workflow"].steps),
            }
            for wid, entry in self._workflow_store.items()
        ]

    async def get_workflow(self, workflow_id: str) -> dict | None:
        entry = self._workflow_store.get(workflow_id)
        if entry is None:
            return None
        wf = entry["workflow"]
        return {
            "id": wf.id,
            "name": wf.name,
            "description": wf.description,
            "version": wf.version,
            "status": wf.status.value,
            "steps": [
                {
                    "id": s.id,
                    "name": s.name,
                    "type": s.step_type.value,
                    "status": s.status.value,
                    "dependsOn": s.depends_on,
                    "handler": s.task.handler if s.task else None,
                    "error": s.error,
                }
                for s in wf.steps
            ],
            "context": dict(wf.context),
            "createdAt": wf.created_at,
            "tags": wf.tags,
        }

    async def run_pipeline(
        self,
        task_specs: list[dict[str, Any]],
        name: str = "pipeline",
        context: dict[str, Any] | None = None,
    ) -> dict:
        """Convenience: create and run a pipeline in one call."""
        created = await self.create_workflow(name, task_specs, context=context)
        result = await self.run_workflow(created["id"], context)
        return result
