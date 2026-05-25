from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable


class WorkflowStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class StepType(str, Enum):
    TASK = "task"
    CONDITIONAL = "conditional"
    PARALLEL = "parallel"
    TOOL_CALL = "tool_call"
    SUB_WORKFLOW = "sub_workflow"
    HUMAN_INPUT = "human_input"
    WAIT = "wait"


class StepStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    WAITING = "waiting"


class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"


@dataclass
class RetryPolicy:
    """Configuration for step retry behavior."""

    max_retries: int = 3
    base_delay_ms: float = 1000.0
    max_delay_ms: float = 30000.0
    backoff_multiplier: float = 2.0
    retry_on_timeout: bool = True
    retry_on_error: bool = True
    retryable_error_codes: list[str] | None = None


@dataclass
class ConditionalBranch:
    """A branch in a conditional step."""

    condition: str  # Python expression evaluated against context
    step_ids: list[str]  # Steps to run if condition is true
    description: str = ""


@dataclass
class ParallelGroup:
    """A group of steps that run in parallel."""

    step_ids: list[str]
    max_concurrency: int = 5
    fail_fast: bool = False  # Cancel all if one fails


@dataclass
class Task:
    """A single executable unit within a step."""

    id: str
    name: str
    handler: str  # Registered handler name, resolved at runtime
    params: dict[str, Any] = field(default_factory=dict)
    status: TaskStatus = TaskStatus.PENDING
    result: Any = None
    error: str | None = None
    started_at: float | None = None
    completed_at: float | None = None


@dataclass
class WorkflowStep:
    """A single step in a workflow DAG."""

    id: str
    name: str
    step_type: StepType = StepType.TASK
    description: str = ""
    task: Task | None = None
    depends_on: list[str] = field(default_factory=list)  # IDs of steps that must complete first
    conditional_branches: list[ConditionalBranch] = field(default_factory=list)
    parallel_group: ParallelGroup | None = None
    retry_policy: RetryPolicy | None = None
    timeout_seconds: float | None = None
    input_transform: str | None = None  # Python expression to transform inputs
    output_transform: str | None = None  # Python expression to transform outputs
    status: StepStatus = StepStatus.PENDING
    result: Any = None
    error: str | None = None
    started_at: float | None = None
    completed_at: float | None = None


@dataclass
class Workflow:
    """A complete workflow definition — a DAG of steps."""

    id: str
    name: str
    description: str = ""
    version: str = "1.0.0"
    steps: list[WorkflowStep] = field(default_factory=list)
    status: WorkflowStatus = WorkflowStatus.PENDING
    context: dict[str, Any] = field(default_factory=dict)  # Shared state across steps
    created_at: float | None = None
    started_at: float | None = None
    completed_at: float | None = None
    error: str | None = None
    tags: list[str] = field(default_factory=list)

    def get_step(self, step_id: str) -> WorkflowStep | None:
        for step in self.steps:
            if step.id == step_id:
                return step
        return None

    def get_ready_steps(self) -> list[WorkflowStep]:
        """Return steps whose dependencies are all completed."""
        ready: list[WorkflowStep] = []
        for step in self.steps:
            if step.status != StepStatus.PENDING:
                continue
            if all(
                self.get_step(dep) and self.get_step(dep).status == StepStatus.COMPLETED
                for dep in step.depends_on
            ):
                ready.append(step)
        return ready

    def get_entry_steps(self) -> list[WorkflowStep]:
        """Steps with no dependencies — start here."""
        return [s for s in self.steps if not s.depends_on and s.status == StepStatus.PENDING]


@dataclass
class WorkflowResult:
    """Result of a workflow execution."""

    workflow_id: str
    status: WorkflowStatus
    step_results: dict[str, Any] = field(default_factory=dict)
    context: dict[str, Any] = field(default_factory=dict)
    error: str | None = None
    total_steps: int = 0
    completed_steps: int = 0
    failed_steps: int = 0
    duration_ms: float = 0.0
