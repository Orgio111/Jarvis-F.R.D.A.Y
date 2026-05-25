from __future__ import annotations

import asyncio
import time
from typing import Any, Callable

from workflow_engine.models import (
    ConditionalBranch,
    ParallelGroup,
    RetryPolicy,
    StepStatus,
    StepType,
    TaskStatus,
    Workflow,
    WorkflowResult,
    WorkflowStatus,
    WorkflowStep,
)
from workflow_engine.retry import RetryHandler


class WorkflowExecutor:
    """Deterministic workflow execution engine — runs a DAG of steps."""

    def __init__(self) -> None:
        self._handlers: dict[str, Callable[..., Any]] = {}
        self._retry_handler = RetryHandler()

    def register_handler(self, name: str, handler: Callable[..., Any]) -> None:
        """Register a callable by name that steps can reference."""
        self._handlers[name] = handler

    def register_handlers(self, handlers: dict[str, Callable[..., Any]]) -> None:
        self._handlers.update(handlers)

    async def execute(
        self,
        workflow: Workflow,
        initial_context: dict[str, Any] | None = None,
    ) -> WorkflowResult:
        """Execute a full workflow DAG and return results."""
        start = time.monotonic()
        workflow.status = WorkflowStatus.RUNNING
        workflow.started_at = start

        if initial_context:
            workflow.context.update(initial_context)

        step_results: dict[str, Any] = {}
        failed_steps = 0
        completed_steps = 0

        try:
            while True:
                ready = workflow.get_ready_steps()
                if not ready:
                    break

                for step in ready:
                    step.status = StepStatus.RUNNING
                    step.started_at = time.monotonic()

                    try:
                        result = await self._execute_step(workflow, step)
                        step.status = StepStatus.COMPLETED
                        step.result = result
                        step.completed_at = time.monotonic()
                        step_results[step.id] = result
                        completed_steps += 1
                    except Exception as exc:
                        step.status = StepStatus.FAILED
                        step.error = str(exc)
                        step_results[step.id] = {"error": str(exc)}
                        failed_steps += 1

                        # If a dependency failed, skip dependent steps
                        dependent = self._find_dependents(workflow, step.id)
                        for dep_step in dependent:
                            dep_step.status = StepStatus.SKIPPED
                            dep_step.error = f"dependency_failed:{step.id}"

                # Check if any remaining steps have unmet dependencies due to failures
                for step in workflow.steps:
                    if step.status != StepStatus.PENDING:
                        continue
                    for dep_id in step.depends_on:
                        dep = workflow.get_step(dep_id)
                        if dep and dep.status == StepStatus.FAILED:
                            step.status = StepStatus.SKIPPED
                            step.error = f"dependency_failed:{dep_id}"
                            step_results[step.id] = {"error": step.error}
                            break

            # Determine final status
            if failed_steps > 0:
                workflow.status = WorkflowStatus.FAILED
            else:
                workflow.status = WorkflowStatus.COMPLETED

        except asyncio.CancelledError:
            workflow.status = WorkflowStatus.CANCELLED
            for step in workflow.steps:
                if step.status == StepStatus.RUNNING:
                    step.status = StepStatus.FAILED
                    step.error = "workflow_cancelled"

        except Exception as exc:
            workflow.status = WorkflowStatus.FAILED
            workflow.error = str(exc)

        finally:
            duration = (time.monotonic() - start) * 1000
            workflow.completed_at = time.monotonic()

            return WorkflowResult(
                workflow_id=workflow.id,
                status=workflow.status,
                step_results=step_results,
                context=workflow.context,
                error=workflow.error,
                total_steps=len(workflow.steps),
                completed_steps=completed_steps,
                failed_steps=failed_steps,
                duration_ms=duration,
            )

    async def _execute_step(
        self,
        workflow: Workflow,
        step: WorkflowStep,
    ) -> Any:
        """Execute a single step based on its type."""
        if step.step_type == StepType.TASK:
            return await self._execute_task_step(workflow, step)

        elif step.step_type == StepType.CONDITIONAL:
            return await self._execute_conditional_step(workflow, step)

        elif step.step_type == StepType.PARALLEL:
            return await self._execute_parallel_step(workflow, step)

        elif step.step_type == StepType.TOOL_CALL:
            return await self._execute_tool_call_step(workflow, step)

        elif step.step_type == StepType.SUB_WORKFLOW:
            return await self._execute_sub_workflow_step(workflow, step)

        elif step.step_type == StepType.WAIT:
            return await self._execute_wait_step(workflow, step)

        elif step.step_type == StepType.HUMAN_INPUT:
            return {"status": "waiting", "message": "Waiting for human input"}
        else:
            raise ValueError(f"Unknown step type: {step.step_type}")

    async def _execute_task_step(self, workflow: Workflow, step: WorkflowStep) -> Any:
        task = step.task
        if task is None:
            raise ValueError(f"Step {step.id} has no task")

        task.status = TaskStatus.RUNNING
        task.started_at = time.monotonic()

        handler = self._handlers.get(task.handler)
        if handler is None:
            raise ValueError(f"No handler registered for '{task.handler}'")

        # Merge step params with context for input
        params = dict(task.params)
        if step.input_transform:
            try:
                resolved = eval(step.input_transform, {"ctx": dict(workflow.context), "params": params})
                if isinstance(resolved, dict):
                    params.update(resolved)
            except Exception as exc:
                raise ValueError(f"Input transform failed for step {step.id}: {exc}") from exc

        async def execute() -> Any:
            if asyncio.iscoroutinefunction(handler):
                return await handler(**params)
            return handler(**params)

        if step.retry_policy:
            result = await self._retry_handler.execute_with_retry(
                execute, step.retry_policy, step_id=step.id,
            )
        elif step.timeout_seconds:
            try:
                result = await asyncio.wait_for(execute(), timeout=step.timeout_seconds)
            except asyncio.TimeoutError:
                raise TimeoutError(f"Step {step.id} timed out after {step.timeout_seconds}s")
        else:
            result = await execute()

        task.status = TaskStatus.COMPLETED
        task.result = result
        task.completed_at = time.monotonic()

        # Output transform
        if step.output_transform:
            try:
                result = eval(step.output_transform, {"ctx": workflow.context, "result": result})
            except Exception as exc:
                raise ValueError(f"Output transform failed for step {step.id}: {exc}") from exc

        # Store in shared context
        workflow.context[step.id] = result
        return result

    async def _execute_conditional_step(self, workflow: Workflow, step: WorkflowStep) -> dict[str, Any]:
        for branch in step.conditional_branches:
            try:
                condition_result = eval(branch.condition, {"ctx": dict(workflow.context)})
                if condition_result:
                    # Run the branch steps
                    branch_results: dict[str, Any] = {}
                    for step_id in branch.step_ids:
                        sub_step = workflow.get_step(step_id)
                        if sub_step:
                            sub_step.status = StepStatus.RUNNING
                            try:
                                result = await self._execute_step(workflow, sub_step)
                                sub_step.status = StepStatus.COMPLETED
                                sub_step.result = result
                                branch_results[step_id] = result
                            except Exception as exc:
                                sub_step.status = StepStatus.FAILED
                                sub_step.error = str(exc)
                                branch_results[step_id] = {"error": str(exc)}
                    return {"branch": branch.description, "results": branch_results}
            except Exception as exc:
                raise ValueError(f"Condition evaluation failed for step {step.id}: {exc}") from exc

        return {"branch": "none", "results": None}

    async def _execute_parallel_step(self, workflow: Workflow, step: WorkflowStep) -> dict[str, Any]:
        group = step.parallel_group
        if group is None:
            raise ValueError(f"Parallel step {step.id} has no parallel_group")

        sub_steps = [workflow.get_step(sid) for sid in group.step_ids if workflow.get_step(sid)]
        if not sub_steps:
            return {"results": {}}

        semaphore = asyncio.Semaphore(group.max_concurrency)

        async def run_sub_step(sub_step: WorkflowStep) -> tuple[str, Any]:
            async with semaphore:
                sub_step.status = StepStatus.RUNNING
                try:
                    result = await self._execute_step(workflow, sub_step)
                    sub_step.status = StepStatus.COMPLETED
                    sub_step.result = result
                    return sub_step.id, result
                except Exception as exc:
                    sub_step.status = StepStatus.FAILED
                    sub_step.error = str(exc)
                    if group.fail_fast:
                        raise
                    return sub_step.id, {"error": str(exc)}

        tasks = [asyncio.create_task(run_sub_step(ss)) for ss in sub_steps]
        done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_EXCEPTION if group.fail_fast else asyncio.ALL_COMPLETED)

        # Cancel pending if fail_fast
        if group.fail_fast and any(t.exception() for t in done if t.done()):
            for t in pending:
                t.cancel()
            for ss in sub_steps:
                if ss.status == StepStatus.RUNNING:
                    ss.status = StepStatus.FAILED
                    ss.error = "cancelled_by_fail_fast"

        results = {}
        for t in done:
            try:
                sid, result = t.result()
                results[sid] = result
            except Exception as exc:
                for ss in sub_steps:
                    if ss.status == StepStatus.RUNNING:
                        ss.status = StepStatus.FAILED
                        ss.error = str(exc)
                        results[ss.id] = {"error": str(exc)}

        return {"results": results, "parallel_group": step.id}

    async def _execute_tool_call_step(self, workflow: Workflow, step: WorkflowStep) -> Any:
        return await self._execute_task_step(workflow, step)

    async def _execute_sub_workflow_step(self, workflow: Workflow, step: WorkflowStep) -> dict[str, Any]:
        # Sub-workflows are executed by the orchestrator
        return {"status": "delegated", "sub_workflow_step": step.id}

    async def _execute_wait_step(self, workflow: Workflow, step: WorkflowStep) -> dict[str, Any]:
        task = step.task
        if task and "duration_seconds" in task.params:
            duration = float(task.params["duration_seconds"])
            await asyncio.sleep(duration)
            return {"waited_seconds": duration}
        return {"status": "wait_completed"}

    @staticmethod
    def _find_dependents(workflow: Workflow, step_id: str) -> list[WorkflowStep]:
        return [s for s in workflow.steps if step_id in s.depends_on]
