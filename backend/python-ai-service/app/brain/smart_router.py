"""
Smart Router — cost-aware, latency-aware, confidence-based model selection.

Routing criteria:
  - latency: faster models for simple tasks
  - accuracy: smarter models for complex reasoning
  - cost: cheaper models for high-volume / low-stakes tasks
  - context_size: different models have different context windows
  - task_type: specialized models for specific domains
  - confidence: fallback to better models when confidence is low

Task Complexity Levels:
  - TRIVIAL: simple lookups, yes/no answers → fastest/cheapest
  - SIMPLE: straightforward reasoning, basic code → fast
  - MODERATE: multi-step reasoning, complex code → balanced
  - COMPLEX: deep reasoning, architecture, research → smart/deep
  - CRITICAL: maximum accuracy required → best available

Default model routing (matches model_modes.py):
  - TRIVIAL → FAST
  - SIMPLE → FAST
  - MODERATE → SMART
  - COMPLEX → DEEP
  - CRITICAL → DEEP
  - CODE → CODING
"""
from __future__ import annotations

from enum import Enum
from typing import Any

from app.core.logging import get_logger
from app.core.model_modes import ChatMode, ALL_MODES

logger = get_logger(__name__)


class TaskComplexity(Enum):
    TRIVIAL = "trivial"
    SIMPLE = "simple"
    MODERATE = "moderate"
    COMPLEX = "complex"
    CRITICAL = "critical"


class TaskType(Enum):
    GENERAL = "general"
    CODE = "code"
    RESEARCH = "research"
    CREATIVE = "creative"
    ANALYSIS = "analysis"
    PLANNING = "planning"
    DEBUGGING = "debugging"
    EXPLANATION = "explanation"
    SUMMARIZATION = "summarization"
    ROUTING = "routing"


# Complexity → recommended mode mapping
COMPLEXITY_TO_MODE: dict[TaskComplexity, ChatMode] = {
    TaskComplexity.TRIVIAL: "fast",
    TaskComplexity.SIMPLE: "fast",
    TaskComplexity.MODERATE: "smart",
    TaskComplexity.COMPLEX: "deep",
    TaskComplexity.CRITICAL: "deep",
}

# Task type → complexity mapping (overridable)
TASK_TYPE_COMPLEXITY: dict[TaskType, TaskComplexity] = {
    TaskType.GENERAL: TaskComplexity.SIMPLE,
    TaskType.CODE: TaskComplexity.MODERATE,
    TaskType.RESEARCH: TaskComplexity.COMPLEX,
    TaskType.CREATIVE: TaskComplexity.MODERATE,
    TaskType.ANALYSIS: TaskComplexity.MODERATE,
    TaskType.PLANNING: TaskComplexity.COMPLEX,
    TaskType.DEBUGGING: TaskComplexity.MODERATE,
    TaskType.EXPLANATION: TaskComplexity.SIMPLE,
    TaskType.SUMMARIZATION: TaskComplexity.TRIVIAL,
    TaskType.ROUTING: TaskComplexity.TRIVIAL,
}

# Estimated cost per 1K tokens (USD, approximate)
MODEL_COST_ESTIMATES: dict[ChatMode, float] = {
    "fast": 0.00015,
    "smart": 0.0005,
    "deep": 0.002,
    "coding": 0.0004,
}


class SmartRouter:
    """
    Analyzes incoming tasks and recommends the optimal model,
    agent, and execution strategy.
    """

    _instance: SmartRouter | None = None

    def __init__(self):
        self._routing_history: list[dict] = []

    @classmethod
    def initialize(cls) -> SmartRouter:
        cls._instance = cls()
        return cls._instance

    @classmethod
    def get(cls) -> SmartRouter:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def analyze_task(
        self,
        task: str,
        task_type: str = "general",
        explicit_complexity: str | None = None,
        user_preferred_mode: str | None = None,
    ) -> dict[str, Any]:
        """
        Analyze a task and return routing recommendations.

        Returns:
        {
            "recommendedMode": "fast"|"smart"|"deep"|"coding",
            "complexity": "trivial"|"simple"|"moderate"|"complex"|"critical",
            "taskType": "general"|"code"|"research"|...,
            "confidence": float (0-1),
            "estimatedCostPer1K": float,
            "shouldParallelize": bool,
            "shouldRetry": bool,
            "reasoning": str,
            "suggestedAgents": list[str],
        }
        """
        # Determine task type
        try:
            task_type_enum = TaskType(task_type)
        except ValueError:
            task_type_enum = TaskType.GENERAL

        # Determine complexity
        if explicit_complexity:
            try:
                complexity = TaskComplexity(explicit_complexity)
            except ValueError:
                complexity = TASK_TYPE_COMPLEXITY.get(task_type_enum, TaskComplexity.SIMPLE)
        else:
            # Infer from task length, structure, and keywords
            complexity = self._infer_complexity(task, task_type_enum)

        # Map to mode
        mode = COMPLEXITY_TO_MODE.get(complexity, "fast")

        # User preference overrides
        if user_preferred_mode and user_preferred_mode in ALL_MODES:
            mode = user_preferred_mode

        # Task-type specific overrides
        if task_type_enum == TaskType.CODE and not user_preferred_mode:
            mode = "coding"

        # Calculate confidence
        confidence = self._calc_confidence(complexity, len(task))

        # Parallelization decision
        should_parallelize = complexity in (TaskComplexity.COMPLEX, TaskComplexity.CRITICAL)

        # Retry decision
        should_retry = complexity in (TaskComplexity.MODERATE, TaskComplexity.COMPLEX, TaskComplexity.CRITICAL)

        # Suggested agents based on task type
        suggested_agents = self._suggest_agents(task_type_enum)

        result = {
            "recommendedMode": mode,
            "complexity": complexity.value,
            "taskType": task_type_enum.value,
            "confidence": round(confidence, 3),
            "estimatedCostPer1K": MODEL_COST_ESTIMATES.get(mode, 0.00015),
            "shouldParallelize": should_parallelize,
            "shouldRetry": should_retry,
            "reasoning": self._build_reasoning(complexity, mode, task_type_enum, confidence),
            "suggestedAgents": suggested_agents,
        }

        self._routing_history.append(result)
        return result

    def _infer_complexity(self, task: str, task_type: TaskType) -> TaskComplexity:
        """Infer task complexity from content analysis."""
        task_lower = task.lower()
        task_len = len(task)

        # Critical indicators
        critical_keywords = [
            "security", "vulnerability", "exploit", "production", "deployment",
            "critical", "urgent", "emergency", "data loss", "crash",
            "million", "billion", "revenue", "compliance", "regulation",
        ]
        if any(kw in task_lower for kw in critical_keywords):
            return TaskComplexity.CRITICAL

        # Complex indicators
        complex_keywords = [
            "architecture", "design", "architect", "system design",
            "distributed", "microservice", "optimize", "scalability",
            "research", "analyze", "investigate", "comparison",
            "migration", "refactor", "strategy", "roadmap",
        ]
        if any(kw in task_lower for kw in complex_keywords):
            return TaskComplexity.COMPLEX

        # Moderate indicators
        moderate_keywords = [
            "implement", "build", "create", "develop", "write code",
            "debug", "fix", "test", "integrate", "configure",
            "pipeline", "workflow", "automation",
        ]
        if any(kw in task_lower for kw in moderate_keywords):
            return TaskComplexity.MODERATE

        # Trivial indicators
        if task_len < 50:
            return TaskComplexity.TRIVIAL

        # Default by task type
        return TASK_TYPE_COMPLEXITY.get(task_type, TaskComplexity.SIMPLE)

    def _calc_confidence(self, complexity: TaskComplexity, task_length: int) -> float:
        """Calculate routing confidence based on task characteristics."""
        base_confidence = 0.9
        if complexity == TaskComplexity.CRITICAL:
            base_confidence = 0.7
        elif complexity == TaskComplexity.COMPLEX:
            base_confidence = 0.75
        elif complexity == TaskComplexity.MODERATE:
            base_confidence = 0.85

        # Longer tasks tend to be more complex and harder to route perfectly
        if task_length > 2000:
            base_confidence -= 0.1
        elif task_length > 500:
            base_confidence -= 0.05

        return max(0.3, base_confidence)

    def _suggest_agents(self, task_type: TaskType) -> list[str]:
        """Suggest appropriate sector brains for a task type."""
        mapping = {
            TaskType.CODE: ["coding"],
            TaskType.RESEARCH: ["research"],
            TaskType.CREATIVE: ["creative", "ui_ux"],
            TaskType.ANALYSIS: ["data", "research"],
            TaskType.PLANNING: ["macro_brain", "strategy_brain"],
            TaskType.DEBUGGING: ["coding", "security"],
            TaskType.EXPLANATION: ["research"],
            TaskType.SUMMARIZATION: ["data"],
            TaskType.ROUTING: ["macro_brain"],
            TaskType.GENERAL: ["macro_brain"],
        }
        return mapping.get(task_type, ["macro_brain"])

    def _build_reasoning(
        self,
        complexity: TaskComplexity,
        mode: ChatMode,
        task_type: TaskType,
        confidence: float,
    ) -> str:
        reasons = {
            TaskComplexity.TRIVIAL: f"Trivial {task_type.value} task — fast mode is sufficient",
            TaskComplexity.SIMPLE: f"Simple {task_type.value} task — fast mode is appropriate",
            TaskComplexity.MODERATE: f"Moderate {task_type.value} task — smart mode recommended",
            TaskComplexity.COMPLEX: f"Complex {task_type.value} task — deep reasoning required",
            TaskComplexity.CRITICAL: f"Critical {task_type.value} task — maximum depth needed",
        }
        reason = reasons.get(complexity, f"Routed to {mode} mode")
        return f"{reason} (confidence: {confidence:.0%})"

    def get_routing_history(self, limit: int = 20) -> list[dict]:
        return self._routing_history[-limit:]
