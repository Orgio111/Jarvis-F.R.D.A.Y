"""Unit tests for Agent Reputation System.

Tests cover:
  - AgentReputationRecord properties (win_rate, trust_score, avg_confidence, avg_latency)
  - Recording tasks (success/failure), per-task-type specializations
  - AgentReputation singleton pattern, get_or_create, record
  - Ranking by trust_score, best_for_task selection
  - Edge cases: empty records, zero tasks, extreme values
"""
from __future__ import annotations

import pytest

from app.brain.agent_reputation import AgentReputation, AgentReputationRecord


# ── AgentReputationRecord ────────────────────────────────────────────────────


class TestAgentReputationRecord:
    def test_default_properties(self):
        rec = AgentReputationRecord("test_agent")
        assert rec.agent_id == "test_agent"
        assert rec.agent_type == "agent"
        assert rec.total_tasks == 0
        assert rec.successful_tasks == 0
        assert rec.failed_tasks == 0
        assert rec.win_rate == 0.0
        assert rec.avg_confidence == 0.0
        assert rec.avg_latency_ms == 0.0
        assert rec.trust_score == 0.5  # neutral starting score

    def test_record_success(self):
        rec = AgentReputationRecord("agent_a")
        rec.record_task(success=True, confidence=0.9, latency_ms=100, cost_estimate=0.01, task_type="coding")
        assert rec.total_tasks == 1
        assert rec.successful_tasks == 1
        assert rec.failed_tasks == 0
        assert rec.win_rate == 1.0
        assert rec.avg_confidence == 0.9
        assert rec.avg_latency_ms == 100.0

    def test_record_failure(self):
        rec = AgentReputationRecord("agent_b")
        rec.record_task(success=False, confidence=0.5, latency_ms=200)
        assert rec.total_tasks == 1
        assert rec.successful_tasks == 0
        assert rec.failed_tasks == 1
        assert rec.win_rate == 0.0

    def test_trust_score_composite(self):
        """trust_score = 0.7 * win_rate + 0.3 * avg_confidence"""
        rec = AgentReputationRecord("agent_c")
        rec.record_task(success=True, confidence=1.0)
        rec.record_task(success=True, confidence=1.0)
        # win_rate = 1.0, avg_confidence = 1.0 → trust_score = 0.7*1.0 + 0.3*1.0 = 1.0
        assert rec.trust_score == 1.0

        rec.record_task(success=False, confidence=0.0)
        # win_rate = 2/3 ≈ 0.6667, avg_confidence = 2.0/3 ≈ 0.6667
        # trust_score = 0.7 * 0.6667 + 0.3 * 0.6667 = 0.6667
        assert rec.win_rate == pytest.approx(0.6667, abs=0.001)
        assert rec.avg_confidence == pytest.approx(0.6667, abs=0.001)
        assert rec.trust_score == pytest.approx(0.6667, abs=0.001)

    def test_specialization_score(self):
        rec = AgentReputationRecord("agent_d")
        rec.record_task(success=True, task_type="coding")
        rec.record_task(success=True, task_type="coding")
        rec.record_task(success=False, task_type="research")
        assert rec.get_specialization_score("coding") == 1.0
        assert rec.get_specialization_score("research") == 0.0
        assert rec.get_specialization_score("unknown") == 0.0

    def test_avg_latency(self):
        rec = AgentReputationRecord("agent_e")
        rec.record_task(success=True, latency_ms=100)
        rec.record_task(success=True, latency_ms=300)
        assert rec.avg_latency_ms == 200.0

    def test_to_dict_includes_all_fields(self):
        rec = AgentReputationRecord("agent_f")
        rec.record_task(success=True, confidence=0.9, latency_ms=150, cost_estimate=0.02, task_type="general")
        d = rec.to_dict()
        assert d["agentId"] == "agent_f"
        # trust_score = 0.7 * win_rate + 0.3 * avg_confidence
        # win_rate = 1.0, avg_confidence = 0.9 → trust_score = 0.97
        assert d["trustScore"] == 0.97
        assert d["winRate"] == 1.0
        assert d["avgConfidence"] == 0.9
        assert d["totalTasks"] == 1
        assert d["successfulTasks"] == 1
        assert d["failedTasks"] == 0
        assert "createdAt" in d
        assert "lastUpdated" in d


# ── AgentReputation (singleton tracker) ──────────────────────────────────────


class TestAgentReputation:
    def test_singleton(self):
        AgentReputation._instance = None  # reset
        a = AgentReputation.get()
        b = AgentReputation.get()
        assert a is b

    def test_initialize_creates_new_instance(self):
        AgentReputation._instance = None
        inst = AgentReputation.initialize()
        assert AgentReputation.get() is inst

    def test_get_or_create_creates_if_missing(self):
        rep = AgentReputation()
        rec = rep.get_or_create("new_agent", agent_type="sector_brain")
        assert rec.agent_id == "new_agent"
        assert rec.agent_type == "sector_brain"
        assert rec.total_tasks == 0

    def test_get_or_create_returns_existing(self):
        rep = AgentReputation()
        rep.record("existing", success=True)
        rec = rep.get_or_create("existing")
        assert rec.total_tasks == 1

    def test_record_creates_and_updates(self):
        rep = AgentReputation()
        rec = rep.record("agent_x", success=True, confidence=0.95, latency_ms=50, task_type="code")
        assert rec.total_tasks == 1
        assert rec.successful_tasks == 1
        assert rec.avg_confidence == 0.95

    def test_get_ranking_sorted_by_trust_score(self):
        rep = AgentReputation()
        rep.record("low", success=False, confidence=0.3)
        rep.record("high", success=True, confidence=0.99, latency_ms=10, task_type="code")
        rep.record("medium", success=True, confidence=0.7)
        ranking = rep.get_ranking()
        assert len(ranking) == 3
        assert ranking[0]["agentId"] == "high"
        assert ranking[2]["agentId"] == "low"

    def test_get_ranking_min_tasks_filter(self):
        rep = AgentReputation()
        rep.record("busy", success=True)
        rep.record("busy", success=True)
        rep.record("lazy", success=True)  # only 1 task
        ranking = rep.get_ranking(min_tasks=2)
        assert len(ranking) == 1
        assert ranking[0]["agentId"] == "busy"

    def test_get_ranking_agent_type_filter(self):
        rep = AgentReputation()
        rep.record("agent_a", success=True, agent_type="agent")
        rep.record("brain_a", success=True, agent_type="brain")
        ranking = rep.get_ranking(agent_type="brain")
        assert len(ranking) == 1
        assert ranking[0]["agentId"] == "brain_a"

    def test_get_best_for_task_returns_highest_specialization(self):
        rep = AgentReputation()
        rep.record("gen_agent", success=True, task_type="general")
        rep.record("gen_agent", success=True, task_type="general")
        rep.record("code_pro", success=True, task_type="coding")
        rep.record("code_pro", success=True, task_type="coding")
        best = rep.get_best_for_task("coding")
        assert best is not None
        assert best.agent_id == "code_pro"

    def test_get_best_for_task_returns_none_when_no_data(self):
        rep = AgentReputation()
        best = rep.get_best_for_task("unknown_type")
        assert best is None

    def test_get_best_for_task_min_tasks_filter(self):
        rep = AgentReputation()
        rep.record("barely", success=True, task_type="coding")  # only 1 task, below min_tasks=2
        rep.record("pro", success=True, task_type="coding")
        rep.record("pro", success=True, task_type="coding")
        best = rep.get_best_for_task("coding", min_tasks=2)
        assert best is not None
        assert best.agent_id == "pro"

    def test_get_record_returns_dict_for_existing(self):
        rep = AgentReputation()
        rep.record("known", success=True)
        d = rep.get_record("known")
        assert d is not None
        assert d["agentId"] == "known"

    def test_get_record_returns_none_for_missing(self):
        rep = AgentReputation()
        assert rep.get_record("unknown") is None

    def test_get_all_records_empty(self):
        rep = AgentReputation()
        assert rep.get_all_records() == []

    def test_get_all_records_returns_all(self):
        rep = AgentReputation()
        rep.record("a", success=True)
        rep.record("b", success=True)
        assert len(rep.get_all_records()) == 2

    def test_specialization_appears_in_to_dict(self):
        rep = AgentReputation()
        rep.record("spec_agent", success=True, task_type="coding")
        rep.record("spec_agent", success=True, task_type="coding")
        rep.record("spec_agent", success=False, task_type="research")
        d = rep.get_record("spec_agent")
        assert d is not None
        specializations = d["specializations"]
        assert specializations["coding"] == 1.0
        assert specializations["research"] == 0.0
