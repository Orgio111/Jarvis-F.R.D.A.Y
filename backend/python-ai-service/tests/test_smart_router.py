"""Unit tests for Smart Router.

Tests cover:
  - Task analysis with various types and complexities
  - Complexity inference from keywords and task length
  - Model mode recommendation based on complexity
  - Cost estimation per 1K tokens
  - User-preferred mode override
  - Suggested agents per task type
  - Routing confidence calculation
  - Edge cases: empty task, critical keywords, unknown types
"""
from __future__ import annotations

import pytest

from app.brain.smart_router import (
    SmartRouter,
    TaskComplexity,
    TaskType,
    COMPLEXITY_TO_MODE,
    TASK_TYPE_COMPLEXITY,
    MODEL_COST_ESTIMATES,
)


# ── SmartRouter (singleton + initialization) ─────────────────────────────────


class TestSmartRouterInit:
    def test_singleton(self):
        SmartRouter._instance = None
        a = SmartRouter.get()
        b = SmartRouter.get()
        assert a is b

    def test_initialize_creates_new_instance(self):
        SmartRouter._instance = None
        inst = SmartRouter.initialize()
        assert SmartRouter.get() is inst

    def test_routing_history_starts_empty(self):
        router = SmartRouter()
        assert router.get_routing_history() == []


# ── Task Analysis ─────────────────────────────────────────────────────────────


class TestTaskAnalysis:
    def setup_method(self):
        SmartRouter._instance = None
        self.router = SmartRouter()

    def test_general_task_defaults(self):
        result = self.router.analyze_task("Hello world")
        assert result["taskType"] == "general"
        # "hello world" has no keywords, and is < 50 chars → TRIVIAL
        assert result["complexity"] == "trivial"
        assert result["recommendedMode"] == "fast"
        assert 0 < result["confidence"] <= 1.0
        assert result["estimatedCostPer1K"] == MODEL_COST_ESTIMATES["fast"]

    def test_trivial_task(self):
        result = self.router.analyze_task("Yes or no?")
        assert result["complexity"] == "trivial"
        assert result["recommendedMode"] == "fast"

    def test_simple_task_by_type(self):
        # Long enough to not be trivial, but has no keywords → falls back to task type default
        result = self.router.analyze_task("Explain how Redis caching works under heavy concurrent load with multiple clients", task_type="explanation")
        assert result["complexity"] == "simple"
        assert result["recommendedMode"] == "fast"

    def test_moderate_task(self):
        result = self.router.analyze_task("Implement a FastAPI endpoint with Redis caching")
        assert result["complexity"] == "moderate"
        # MODERATE → smart (default routing; only CODE task_type overrides to "coding")
        assert result["recommendedMode"] == "smart"

    def test_complex_task(self):
        result = self.router.analyze_task("Design the architecture for a distributed microservice system with event sourcing")
        assert result["complexity"] == "complex"
        assert result["recommendedMode"] == "deep"

    def test_critical_task_security(self):
        result = self.router.analyze_task("Fix a critical security vulnerability in production authentication")
        assert result["complexity"] == "critical"
        assert result["recommendedMode"] == "deep"

    def test_critical_task_urgency(self):
        result = self.router.analyze_task("Emergency: data loss in production database")
        assert result["complexity"] == "critical"

    def test_code_task_routes_to_coding(self):
        result = self.router.analyze_task("Write a Python function to sort a list", task_type="code")
        assert result["recommendedMode"] == "coding"
        assert "coding" in result["suggestedAgents"]

    def test_user_preferred_mode_overrides(self):
        result = self.router.analyze_task("Simple question", user_preferred_mode="deep")
        assert result["recommendedMode"] == "deep"

    def test_user_preferred_invalid_mode_falls_back(self):
        result = self.router.analyze_task("Simple question", user_preferred_mode="invalid_mode")
        # Should ignore invalid mode and use default routing
        assert result["recommendedMode"] in ("fast", "smart", "deep", "coding")

    def test_explicit_complexity_override(self):
        result = self.router.analyze_task("Very short task", explicit_complexity="complex")
        assert result["complexity"] == "complex"
        assert result["recommendedMode"] == "deep"

    def test_invalid_explicit_complexity_falls_back(self):
        result = self.router.analyze_task("Explain X", task_type="explanation", explicit_complexity="unknown")
        # Falls back to task-type default (explanation → SIMPLE)
        assert result["complexity"] == "simple"

    def test_invalid_task_type_falls_back_to_general(self):
        result = self.router.analyze_task("Hello", task_type="not_a_real_type")
        assert result["taskType"] == "general"

    def test_research_task(self):
        result = self.router.analyze_task("Research the latest trends in AI agents", task_type="research")
        assert result["taskType"] == "research"
        assert "research" in result["suggestedAgents"]

    def test_creative_task(self):
        result = self.router.analyze_task("Create a logo design concept", task_type="creative")
        assert result["taskType"] == "creative"
        assert "creative" in result["suggestedAgents"] or "ui_ux" in result["suggestedAgents"]

    def test_planning_task(self):
        result = self.router.analyze_task("Plan the Q2 product roadmap", task_type="planning")
        assert result["taskType"] == "planning"
        assert "macro_brain" in result["suggestedAgents"] or "strategy_brain" in result["suggestedAgents"]

    def test_debugging_task(self):
        result = self.router.analyze_task("Debug the memory leak in the worker process", task_type="debugging")
        assert result["taskType"] == "debugging"
        assert "coding" in result["suggestedAgents"]

    def test_routing_task(self):
        result = self.router.analyze_task("Route this to the correct handler", task_type="routing")
        assert result["complexity"] == "trivial"

    def test_long_task_reduces_confidence(self):
        short = self.router.analyze_task("Hello")
        long = self.router.analyze_task("X" * 2500)
        assert long["confidence"] < short["confidence"]

    def test_should_parallelize_for_complex_tasks(self):
        result = self.router.analyze_task("Design a full system architecture", explicit_complexity="complex")
        assert result["shouldParallelize"] is True

    def test_should_not_parallelize_for_simple_tasks(self):
        result = self.router.analyze_task("What's the weather?", explicit_complexity="simple")
        assert result["shouldParallelize"] is False

    def test_should_retry_for_moderate_plus(self):
        trivial = self.router.analyze_task("Yes", explicit_complexity="trivial")
        moderate = self.router.analyze_task("Build a feature", explicit_complexity="moderate")
        critical = self.router.analyze_task("Fix production", explicit_complexity="critical")
        assert trivial["shouldRetry"] is False
        assert moderate["shouldRetry"] is True
        assert critical["shouldRetry"] is True


# ── Complexity Inference ──────────────────────────────────────────────────────


class TestComplexityInference:
    def setup_method(self):
        self.router = SmartRouter()

    def test_trivial_short_task(self):
        c = self.router._infer_complexity("Hi", TaskType.GENERAL)
        assert c == TaskComplexity.TRIVIAL

    def test_critical_keywords(self):
        c = self.router._infer_complexity("Fix security vulnerability in production", TaskType.GENERAL)
        assert c == TaskComplexity.CRITICAL

    def test_complex_keywords(self):
        c = self.router._infer_complexity("Design the architecture for a new system", TaskType.GENERAL)
        assert c == TaskComplexity.COMPLEX

    def test_moderate_keywords(self):
        c = self.router._infer_complexity("Implement a REST API endpoint", TaskType.GENERAL)
        assert c == TaskComplexity.MODERATE

    def test_default_by_task_type(self):
        # Long enough to clear <50 trivial check, no keywords → falls back to RESEARCH default (COMPLEX)
        c = self.router._infer_complexity("Something about code research and analysis of systems", TaskType.RESEARCH)
        assert c == TaskComplexity.COMPLEX  # RESEARCH → COMPLEX

    def test_default_by_task_type_simple(self):
        c = self.router._infer_complexity("Tell me about X", TaskType.SUMMARIZATION)
        assert c == TaskComplexity.TRIVIAL  # SUMMARIZATION → TRIVIAL


# ── Cost Estimates ────────────────────────────────────────────────────────────


class TestCostEstimates:
    def test_all_modes_have_cost(self):
        for mode in ("fast", "smart", "deep", "coding"):
            assert mode in MODEL_COST_ESTIMATES
            assert MODEL_COST_ESTIMATES[mode] > 0

    def test_fast_is_cheapest(self):
        assert MODEL_COST_ESTIMATES["fast"] < MODEL_COST_ESTIMATES["smart"]
        assert MODEL_COST_ESTIMATES["fast"] < MODEL_COST_ESTIMATES["deep"]

    def test_deep_is_most_expensive(self):
        assert MODEL_COST_ESTIMATES["deep"] > MODEL_COST_ESTIMATES["smart"]
        assert MODEL_COST_ESTIMATES["deep"] > MODEL_COST_ESTIMATES["coding"]


# ── Complexity-to-Mode Mapping ────────────────────────────────────────────────


class TestComplexityToMode:
    def test_all_complexities_mapped(self):
        for complexity in TaskComplexity:
            assert complexity in COMPLEXITY_TO_MODE
            assert COMPLEXITY_TO_MODE[complexity] in ("fast", "smart", "deep", "coding")

    def test_code_type_maps_to_coding(self):
        assert TASK_TYPE_COMPLEXITY[TaskType.CODE] == TaskComplexity.MODERATE
        mode = COMPLEXITY_TO_MODE[TaskComplexity.MODERATE]
        # MODERATE → smart by default, but CODE overrides to coding at routing time
        assert mode == "smart"


# ── Routing History ───────────────────────────────────────────────────────────


class TestRoutingHistory:
    def setup_method(self):
        SmartRouter._instance = None
        self.router = SmartRouter()

    def test_history_tracks_analyses(self):
        self.router.analyze_task("Task 1")
        self.router.analyze_task("Task 2")
        history = self.router.get_routing_history()
        assert len(history) == 2
        assert history[0]["taskType"] == "general"

    def test_history_limit(self):
        for i in range(25):
            self.router.analyze_task(f"Task {i}")
        history = self.router.get_routing_history(limit=10)
        assert len(history) == 10
