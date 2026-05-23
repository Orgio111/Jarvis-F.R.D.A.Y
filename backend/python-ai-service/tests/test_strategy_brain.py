"""Unit tests for Strategy Brain.

Tests cover:
  - Fallback plan generation (LLM unavailable)
  - Cost and latency estimation per step and total
  - TaskGraph dataclass construction
  - StrategyStep dataclass defaults
  - to_dict serialization
  - _estimate_total_latency with parallel groups
"""
from __future__ import annotations

import pytest

from app.brain.strategy_brain import StrategyBrain, StrategyStep, TaskGraph


# ── StrategyBrain (singleton + initialization) ────────────────────────────────


class TestStrategyBrainInit:
    def test_singleton(self):
        StrategyBrain._instance = None
        a = StrategyBrain.get()
        b = StrategyBrain.get()
        assert a is b

    def test_initialize_creates_new_instance(self):
        StrategyBrain._instance = None
        inst = StrategyBrain.initialize()
        assert StrategyBrain.get() is inst


# ── Fallback Plan ─────────────────────────────────────────────────────────────


class TestFallbackPlan:
    def setup_method(self):
        StrategyBrain._instance = None
        self.brain = StrategyBrain()

    def test_fallback_plan_returns_three_steps(self):
        plan = self.brain._fallback_plan("Build a web app")
        assert len(plan) == 3
        assert plan[0]["id"] == "step_0"
        assert plan[1]["id"] == "step_1"
        assert plan[2]["id"] == "step_2"

    def test_fallback_plan_has_dependencies(self):
        plan = self.brain._fallback_plan("Test goal")
        assert plan[0]["depends_on"] == []
        assert plan[1]["depends_on"] == ["step_0"]
        assert plan[2]["depends_on"] == ["step_1"]

    def test_fallback_plan_first_step_is_critical(self):
        plan = self.brain._fallback_plan("Goal")
        assert plan[0]["is_critical"] is True
        assert plan[1]["is_critical"] is False

    def test_fallback_plan_includes_goal_in_description(self):
        plan = self.brain._fallback_plan("My special goal")
        assert "My special goal" in plan[0]["description"]

    def test_fallback_plan_default_agent_type(self):
        plan = self.brain._fallback_plan("Goal")
        for step in plan:
            assert step["agent_type"] == "llm"


# ── Cost / Latency Estimation ────────────────────────────────────────────────


class TestCostLatencyEstimation:
    def setup_method(self):
        StrategyBrain._instance = None
        self.brain = StrategyBrain()

    def test_estimate_cost_fast_mode(self):
        cost = self.brain._estimate_cost("fast", 100)
        assert cost > 0
        assert cost < 0.1  # should be very small for fast mode

    def test_estimate_cost_deep_mode(self):
        fast_cost = self.brain._estimate_cost("fast", 100)
        deep_cost = self.brain._estimate_cost("deep", 100)
        assert deep_cost > fast_cost

    def test_estimate_cost_scales_with_length(self):
        short = self.brain._estimate_cost("fast", 10)
        long = self.brain._estimate_cost("fast", 10000)
        assert long > short

    def test_estimate_latency_fast(self):
        lat = self.brain._estimate_latency("fast", "llm")
        assert lat == 1000.0

    def test_estimate_latency_deep(self):
        lat = self.brain._estimate_latency("deep", "llm")
        assert lat == 8000.0

    def test_estimate_latency_tool(self):
        lat = self.brain._estimate_latency("fast", "tool")
        assert lat == 500.0

    def test_estimate_latency_unknown_mode(self):
        lat = self.brain._estimate_latency("unknown", "llm")
        assert lat == 2000.0  # default


# ── Total Latency Estimation ──────────────────────────────────────────────────


class TestTotalLatency:
    def setup_method(self):
        StrategyBrain._instance = None
        self.brain = StrategyBrain()

    def test_sequential_steps_sum(self):
        steps = [
            StrategyStep(id="a", description="a", estimated_latency_ms=1000),
            StrategyStep(id="b", description="b", depends_on=["a"], estimated_latency_ms=2000),
        ]
        total = self.brain._estimate_total_latency(steps)
        assert total == 3000.0

    def test_parallel_groups_take_max(self):
        steps = [
            StrategyStep(id="a1", description="a1", parallel_group="g1", estimated_latency_ms=5000),
            StrategyStep(id="a2", description="a2", parallel_group="g1", estimated_latency_ms=2000),
            StrategyStep(id="b", description="b", estimated_latency_ms=1000),
        ]
        total = self.brain._estimate_total_latency(steps)
        # max(g1) = 5000 + sequential 1000 = 6000
        assert total == 6000.0

    def test_multiple_parallel_groups(self):
        steps = [
            StrategyStep(id="a", description="a", parallel_group="g1", estimated_latency_ms=3000),
            StrategyStep(id="b", description="b", parallel_group="g2", estimated_latency_ms=4000),
        ]
        total = self.brain._estimate_total_latency(steps)
        # g1: 3000, g2: 4000 → 7000
        assert total == 7000.0

    def test_mixed_sequential_and_parallel(self):
        steps = [
            StrategyStep(id="s1", description="s1", estimated_latency_ms=1000),
            StrategyStep(id="p1", description="p1", parallel_group="g1", estimated_latency_ms=5000),
            StrategyStep(id="p2", description="p2", parallel_group="g1", estimated_latency_ms=3000),
            StrategyStep(id="s2", description="s2", depends_on=["p1"], estimated_latency_ms=2000),
        ]
        total = self.brain._estimate_total_latency(steps)
        # sequential: s1(1000) + s2(2000) = 3000
        # parallel g1: max(5000, 3000) = 5000
        # total: 3000 + 5000 = 8000
        assert total == 8000.0

    def test_empty_steps(self):
        total = self.brain._estimate_total_latency([])
        assert total == 0.0


# ── StrategyStep ──────────────────────────────────────────────────────────────


class TestStrategyStep:
    def test_default_values(self):
        step = StrategyStep(id="test", description="A step")
        assert step.agent_type == "llm"
        assert step.sector_brain_id is None
        assert step.model_mode == "fast"
        assert step.parallel_group is None
        assert step.depends_on == []
        assert step.estimated_cost == 0.0
        assert step.estimated_latency_ms == 0.0
        assert step.max_retries == 0
        assert step.timeout_s == 30
        assert step.is_critical is False
        assert step.context_hint == ""

    def test_sector_brain_step(self):
        step = StrategyStep(
            id="step_1",
            description="Generate code",
            agent_type="sector_brain",
            sector_brain_id="coding",
            model_mode="coding",
            parallel_group="build",
            depends_on=["step_0"],
            estimated_cost=0.01,
            estimated_latency_ms=2000,
            is_critical=True,
        )
        assert step.sector_brain_id == "coding"
        assert step.parallel_group == "build"
        assert step.depends_on == ["step_0"]


# ── TaskGraph ─────────────────────────────────────────────────────────────────


class TestTaskGraph:
    def test_default_values(self):
        graph = TaskGraph(goal="Test goal", steps=[])
        assert graph.goal == "Test goal"
        assert graph.steps == []
        assert graph.parallel_groups == 1
        assert graph.estimated_total_cost == 0.0
        assert graph.estimated_total_latency_ms == 0.0
        assert graph.complexity == "moderate"
        assert graph.confidence == 0.85

    def test_with_steps(self):
        step = StrategyStep(id="step_0", description="Analyze")
        graph = TaskGraph(
            goal="Build app",
            steps=[step],
            parallel_groups=2,
            estimated_total_cost=0.05,
            estimated_total_latency_ms=3000,
            complexity="complex",
            confidence=0.9,
        )
        assert len(graph.steps) == 1
        assert graph.steps[0].id == "step_0"
        assert graph.parallel_groups == 2
        assert graph.complexity == "complex"
        assert graph.confidence == 0.9


# ── to_dict ───────────────────────────────────────────────────────────────────


class TestToDict:
    def setup_method(self):
        StrategyBrain._instance = None
        self.brain = StrategyBrain()

    def test_to_dict_serialization(self):
        step = StrategyStep(
            id="step_0",
            description="Analyze the problem",
            agent_type="sector_brain",
            sector_brain_id="research",
            model_mode="smart",
            parallel_group="g1",
            depends_on=[],
            estimated_cost=0.005,
            estimated_latency_ms=3000,
            is_critical=True,
        )
        graph = TaskGraph(
            goal="Research topic",
            steps=[step],
            parallel_groups=1,
            estimated_total_cost=0.005,
            estimated_total_latency_ms=3000,
            complexity="simple",
            confidence=0.9,
        )
        d = self.brain.to_dict(graph)
        assert d["goal"] == "Research topic"
        assert len(d["steps"]) == 1
        assert d["steps"][0]["id"] == "step_0"
        assert d["steps"][0]["sectorBrainId"] == "research"
        assert d["steps"][0]["modelMode"] == "smart"
        assert d["steps"][0]["parallelGroup"] == "g1"
        assert d["steps"][0]["isCritical"] is True
        assert d["estimatedTotalCost"] == 0.005
        assert d["complexity"] == "simple"
