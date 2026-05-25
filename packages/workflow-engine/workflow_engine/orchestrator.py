from __future__ import annotations

import time
import uuid
from typing import Any, Callable

from workflow_engine.executor import WorkflowExecutor
from workflow_engine.models import (
    ConditionalBranch,
    ParallelGroup,
    StepType,
    Task,
    Workflow,
    WorkflowResult,
    WorkflowStatus,
    WorkflowStep,
)


class TaskOrchestrator:
    """Orchestrates multi-step task pipelines — builds workflows from task specs."""

    def __init__(self, executor: WorkflowExecutor | None = None) -> None:
        self._executor = executor or WorkflowExecutor()
        self._handlers: dict[str, Callable[..., Any]] = {}

    def register_handler(self, name: str, handler: Callable[..., Any]) -> None:
        self._handlers[name] = handler
        self._executor.register_handler(name, handler)

    def register_handlers(self, handlers: dict[str, Callable[..., Any]]) -> None:
        self._handlers.update(handlers)
        self._executor.register_handlers(handlers)

    def build_linear_pipeline(
        self,
        workflow_id: str,
        name: str,
        task_specs: list[dict[str, Any]],
        description: str = "",
        context: dict[str, Any] | None = None,
    ) -> Workflow:
        """Build a linear workflow from a list of task specs (each runs after the previous)."""
        steps: list[WorkflowStep] = []
        previous_id: str | None = None

        for i, spec in enumerate(task_specs):
            step_id = spec.get("id", f"step_{i}")
            step = WorkflowStep(
                id=step_id,
                name=spec.get("name", f"Step {i}"),
                step_type=StepType(spec.get("type", "task")),
                description=spec.get("description", ""),
                task=Task(
                    id=f"task_{step_id}",
                    name=spec.get("name", f"Task {i}"),
                    handler=spec.get("handler", ""),
                    params=spec.get("params", {}),
                ),
                depends_on=[previous_id] if previous_id else [],
                retry_policy=spec.get("retry_policy"),
                timeout_seconds=spec.get("timeout_seconds"),
                input_transform=spec.get("input_transform"),
                output_transform=spec.get("output_transform"),
            )
            steps.append(step)
            previous_id = step_id

        return Workflow(
            id=workflow_id,
            name=name,
            description=description,
            steps=steps,
            context=context or {},
            created_at=time.time(),
            tags=["pipeline", "linear"],
        )

    def build_parallel_pipeline(
        self,
        workflow_id: str,
        name: str,
        parallel_branches: list[list[dict[str, Any]]],
        description: str = "",
        context: dict[str, Any] | None = None,
    ) -> Workflow:
        """Build a workflow with parallel branches, each branch being a linear sequence."""
        steps: list[WorkflowStep] = []
        branch_ids: list[str] = []

        for branch_idx, branch_tasks in enumerate(parallel_branches):
            previous_id: str | None = None
            branch_first_id: str | None = None

            for task_idx, spec in enumerate(branch_tasks):
                step_id = spec.get("id", f"branch{branch_idx}_step{task_idx}")
                if branch_first_id is None:
                    branch_first_id = step_id

                step = WorkflowStep(
                    id=step_id,
                    name=spec.get("name", f"Branch {branch_idx} Step {task_idx}"),
                    step_type=StepType(spec.get("type", "task")),
                    description=spec.get("description", ""),
                    task=Task(
                        id=f"task_{step_id}",
                        name=spec.get("name", f"Task {branch_idx}_{task_idx}"),
                        handler=spec.get("handler", ""),
                        params=spec.get("params", {}),
                    ),
                    depends_on=[previous_id] if previous_id else [],
                    retry_policy=spec.get("retry_policy"),
                    timeout_seconds=spec.get("timeout_seconds"),
                )
                steps.append(step)
                previous_id = step_id

            if branch_first_id:
                branch_ids.append(branch_first_id)

        # Create a parallel group step that depends on nothing
        parallel_step = WorkflowStep(
            id="parallel_root",
            name="Parallel Execution",
            step_type=StepType.PARALLEL,
            description="Execute branches in parallel",
            parallel_group=ParallelGroup(
                step_ids=branch_ids,
                max_concurrency=len(branch_ids),
                fail_fast=False,
            ),
        )
        steps.append(parallel_step)

        return Workflow(
            id=workflow_id,
            name=name,
            description=description,
            steps=steps,
            context=context or {},
            created_at=time.time(),
            tags=["pipeline", "parallel"],
        )

    def build_conditional_workflow(
        self,
        workflow_id: str,
        name: str,
        condition_expr: str,
        if_branch: list[dict[str, Any]],
        else_branch: list[dict[str, Any]] | None = None,
        description: str = "",
        context: dict[str, Any] | None = None,
    ) -> Workflow:
        """Build a workflow with conditional branching."""
        steps: list[WorkflowStep] = []
        if_ids: list[str] = []
        else_ids: list[str] = []

        # If-branch tasks
        for i, spec in enumerate(if_branch):
            step_id = spec.get("id", f"if_step_{i}")
            prev_id = if_ids[-1] if if_ids else None
            step = WorkflowStep(
                id=step_id,
                name=spec.get("name", f"If Step {i}"),
                step_type=StepType(spec.get("type", "task")),
                description=spec.get("description", ""),
                task=Task(
                    id=f"task_{step_id}",
                    name=spec.get("name", f"If Task {i}"),
                    handler=spec.get("handler", ""),
                    params=spec.get("params", {}),
                ),
                depends_on=[prev_id] if prev_id else [],
            )
            steps.append(step)
            if_ids.append(step_id)

        # Else-branch tasks
        if else_branch:
            for i, spec in enumerate(else_branch):
                step_id = spec.get("id", f"else_step_{i}")
                prev_id = else_ids[-1] if else_ids else None
                step = WorkflowStep(
                    id=step_id,
                    name=spec.get("name", f"Else Step {i}"),
                    step_type=StepType(spec.get("type", "task")),
                    description=spec.get("description", ""),
                    task=Task(
                        id=f"task_{step_id}",
                        name=spec.get("name", f"Else Task {i}"),
                        handler=spec.get("handler", ""),
                        params=spec.get("params", {}),
                    ),
                    depends_on=[prev_id] if prev_id else [],
                )
                steps.append(step)
                else_ids.append(step_id)

        # Condition step
        branch = ConditionalBranch(
            condition=condition_expr,
            step_ids=if_ids,
            description="if branch",
        )
        else_branch_obj = None
        if else_ids:
            else_branch_obj = ConditionalBranch(
                condition=f"not ({condition_expr})",
                step_ids=else_ids,
                description="else branch",
            )

        condition_step = WorkflowStep(
            id="condition_root",
            name="Condition",
            step_type=StepType.CONDITIONAL,
            description="Conditional branching",
            conditional_branches=[b for b in [branch, else_branch_obj] if b],
        )
        steps.append(condition_step)

        return Workflow(
            id=workflow_id,
            name=name,
            description=description,
            steps=steps,
            context=context or {},
            created_at=time.time(),
            tags=["pipeline", "conditional"],
        )

    async def run_workflow(
        self,
        workflow: Workflow,
        initial_context: dict[str, Any] | None = None,
    ) -> WorkflowResult:
        """Execute a workflow through the executor."""
        return await self._executor.execute(workflow, initial_context)

    async def run_pipeline(
        self,
        task_specs: list[dict[str, Any]],
        name: str = "pipeline",
        context: dict[str, Any] | None = None,
    ) -> WorkflowResult:
        """Convenience: build a linear pipeline and run it."""
        wf = self.build_linear_pipeline(
            workflow_id=f"pipeline_{uuid.uuid4().hex[:8]}",
            name=name,
            task_specs=task_specs,
            context=context,
        )
        return await self.run_workflow(wf)
