"""
Integration tests for the /brain/ endpoints using httpx TestClient.

Tests cover:
  - GET  /brain/status
  - GET  /brain/sectors
  - POST /brain/process
  - POST /brain/plan
  - GET  /brain/reputation
  - GET  /brain/routing
  - POST /brain/sector/{id}
"""
from __future__ import annotations

from unittest.mock import ANY, AsyncMock, patch

import pytest


# ─── Helpers ──────────────────────────────────────────────────────────────────


def _seed_reputation():
    """Add sample reputation records for tests that need them."""
    from app.brain.agent_reputation import AgentReputation

    rep = AgentReputation.get()
    rep.record("sector_coding", True, 0.92, 1200, task_type="code", agent_type="sector_brain")
    rep.record("sector_coding_v2", True, 0.88, 980, task_type="code", agent_type="sector_brain")
    rep.record("sector_research", True, 0.85, 2100, task_type="research", agent_type="sector_brain")
    rep.record("sector_security", False, 0.0, 500, task_type="security", agent_type="sector_brain")
    rep.record("macro_brain", True, 0.90, 800, task_type="general", agent_type="brain")


def _seed_routing():
    """Add sample routing history for tests that need them."""
    from app.brain.smart_router import SmartRouter

    sr = SmartRouter.get()
    sr.analyze_task("Build a REST API", "code")
    sr.analyze_task("Research quantum computing", "research")
    sr.analyze_task("Say hello", "general")


@pytest.fixture(autouse=True)
def _reset_brain():
    """Reset all brain singletons before each test to prevent cross-test pollution."""
    from app.brain.smart_router import SmartRouter
    from app.brain.agent_reputation import AgentReputation
    from app.brain.strategy_brain import StrategyBrain
    from app.brain.macro_brain import MacroBrain

    SmartRouter._instance = None
    AgentReputation._instance = None
    StrategyBrain._instance = None
    MacroBrain._instance = None
    SmartRouter.initialize()
    AgentReputation.initialize()
    StrategyBrain.initialize()
    MacroBrain.initialize()


# ===============================================================================
#  GET /brain/status
# ===============================================================================


class TestBrainStatus:
    """GET /brain/status — full cognitive architecture status."""

    def test_status_returns_200(self, client):
        r = client.get("/brain/status")
        assert r.status_code == 200
        body = r.json()
        assert body["ok"] is True
        data = body["data"]
        assert "macroBrain" in data
        assert "sectorBrains" in data
        assert "reputation" in data
        assert "strategyBrain" in data
        assert "smartRouter" in data

    def test_status_macro_brain_section(self, client):
        data = client.get("/brain/status").json()["data"]
        mb = data["macroBrain"]
        assert mb["initialized"] is True
        assert mb["availableSectors"] == 10

    def test_status_sector_brains_section(self, client):
        data = client.get("/brain/status").json()["data"]["sectorBrains"]
        assert len(data) == 10
        ids = {s["id"] for s in data}
        assert "coding" in ids
        assert "research" in ids
        assert "security" in ids
        assert "memory_brain" in ids

    def test_status_reputation_empty_initially(self, client):
        data = client.get("/brain/status").json()["data"]
        assert data["reputation"]["trackedAgents"] == 0

    def test_status_reputation_after_records(self, client):
        _seed_reputation()
        data = client.get("/brain/status").json()["data"]
        assert data["reputation"]["trackedAgents"] > 0

    def test_status_strategy_brain_section(self, client):
        data = client.get("/brain/status").json()["data"]
        assert data["strategyBrain"]["available"] is True

    def test_status_smart_router_section(self, client):
        data = client.get("/brain/status").json()["data"]
        assert data["smartRouter"]["available"] is True

    def test_status_includes_routing_history(self, client):
        _seed_routing()
        data = client.get("/brain/status").json()["data"]
        history = data["smartRouter"]["routingHistory"]
        assert len(history) >= 2

    def test_status_includes_reputation_rankings(self, client):
        _seed_reputation()
        data = client.get("/brain/status").json()["data"]
        rankings = data["reputation"]["rankings"]
        assert len(rankings) > 0
        # Should be sorted by trust_score descending
        scores = [r["trustScore"] for r in rankings]
        assert scores == sorted(scores, reverse=True)


# ===============================================================================
#  GET /brain/sectors
# ===============================================================================


class TestListSectors:
    """GET /brain/sectors — list all sector brains."""

    def test_sectors_returns_list(self, client):
        r = client.get("/brain/sectors")
        assert r.status_code == 200
        body = r.json()
        assert body["ok"] is True

    def test_sectors_total_is_10(self, client):
        data = client.get("/brain/sectors").json()["data"]
        assert data["total"] == 10

    def test_sectors_contains_all_ids(self, client):
        sectors = client.get("/brain/sectors").json()["data"]["sectors"]
        ids = {s["id"] for s in sectors}
        expected = {"coding", "research", "devops", "security", "memory_brain",
                    "ui_ux", "finance", "creative", "automation", "data"}
        assert ids == expected

    def test_sectors_each_has_metadata(self, client):
        sectors = client.get("/brain/sectors").json()["data"]["sectors"]
        for s in sectors:
            assert "id" in s
            assert "name" in s
            assert "description" in s
            assert "capabilities" in s
            assert isinstance(s["capabilities"], list)

    def test_sectors_coding_brain_name(self, client):
        sectors = client.get("/brain/sectors").json()["data"]["sectors"]
        coding = next(s for s in sectors if s["id"] == "coding")
        assert coding["name"] == "Coding Brain"
        assert len(coding["capabilities"]) > 0


# ===============================================================================
#  POST /brain/process
# ===============================================================================


class TestProcessTask:
    """POST /brain/process — process a task through Macro Brain."""

    def test_missing_task_returns_400(self, client):
        r = client.post("/brain/process", json={})
        assert r.status_code == 400
        assert r.json()["ok"] is False

    def test_empty_task_returns_400(self, client):
        r = client.post("/brain/process", json={"task": ""})
        assert r.status_code == 400
        assert r.json()["ok"] is False

    def test_whitespace_task_returns_400(self, client):
        r = client.post("/brain/process", json={"task": "   "})
        assert r.status_code == 400
        assert r.json()["ok"] is False

    def test_invalid_json_returns_400(self, client):
        r = client.post("/brain/process", content=b"not json",
                        headers={"Content-Type": "application/json"})
        assert r.status_code == 400
        assert r.json()["ok"] is False

    def test_simple_task_returns_routing(self, client):
        """Even without a provider, routing info is returned."""
        r = client.post("/brain/process", json={
            "task": "Say hello",
            "taskType": "general",
        })
        assert r.status_code == 200
        data = r.json()["data"]
        assert "routing" in data
        assert data["routing"]["taskType"] == "general"
        assert data["routing"]["recommendedMode"] in ("fast", "smart", "deep", "coding")

    def test_process_with_preferred_mode(self, client):
        r = client.post("/brain/process", json={
            "task": "Analyze this data",
            "preferredMode": "deep",
        })
        assert r.status_code == 200
        data = r.json()["data"]
        assert data["routing"]["recommendedMode"] == "deep"

    def test_process_with_code_type(self, client):
        r = client.post("/brain/process", json={
            "task": "Write a React component",
            "taskType": "code",
        })
        assert r.status_code == 200
        data = r.json()["data"]
        assert data["routing"]["taskType"] == "code"
        # code tasks without user mode preference map to 'coding' mode
        assert data["routing"]["recommendedMode"] == "coding"

    def test_process_with_sector_brain_returns_200(self, client):
        """Routing to a sector brain gracefully degrades when no provider."""
        r = client.post("/brain/process", json={
            "task": "Sort this list",
            "taskType": "code",
            "sectorBrainId": "coding",
        })
        assert r.status_code == 200
        data = r.json()["data"]
        assert data["routing"]["taskType"] == "code"
        assert len(data["brainResults"]) > 0

    def test_process_with_unknown_sector_brain(self, client):
        """Unknown sector brain falls back to direct LLM."""
        r = client.post("/brain/process", json={
            "task": "Do something",
            "sectorBrainId": "nonexistent",
        })
        assert r.status_code == 200
        data = r.json()["data"]
        # The macro brain should handle gracefully — no crash
        assert "routing" in data

    def test_process_streaming_returns_sse(self, client):
        r = client.post("/brain/process", json={
            "task": "Say hello",
            "stream": True,
        })
        assert r.status_code == 200
        ct = r.headers.get("content-type", "")
        assert "text/event-stream" in ct

    def test_process_streaming_first_event(self, client):
        r = client.post("/brain/process", json={
            "task": "Say hello",
            "stream": True,
        })
        lines = r.text.strip().split("\n")
        assert len(lines) >= 2
        # First data line should contain BRAIN_ROUTING or BRAIN_ERROR
        first_data = lines[0]
        assert first_data.startswith("data: ")
        assert "BRAIN_ROUTING" in first_data or "BRAIN_ERROR" in first_data

    def test_process_with_critical_task_type(self, client):
        r = client.post("/brain/process", json={
            "task": "Fix a security vulnerability",
            "taskType": "security",
        })
        assert r.status_code == 200
        data = r.json()["data"]
        assert data["routing"]["complexity"] == "critical"

    def test_process_tracks_reputation(self, client):
        client.post("/brain/process", json={
            "task": "Say hello",
            "taskType": "general",
        })
        from app.brain.agent_reputation import AgentReputation
        records = AgentReputation.get().get_all_records()
        assert len(records) > 0

    def test_process_with_mocked_provider_returns_output(self, client):
        """Full integration test with a mocked provider."""
        with patch("app.providers.router.ProviderRouter.get") as mock_get:
            mock_provider = AsyncMock()
            mock_provider.chat.return_value = {
                "choices": [{"message": {"content": "Hello from JARVIS!"}}]
            }
            mock_router = AsyncMock()
            mock_router.get_active_provider.return_value = mock_provider
            mock_get.return_value = mock_router

            r = client.post("/brain/process", json={
                "task": "Say hello",
                "taskType": "general",
            })
            assert r.status_code == 200
            data = r.json()["data"]
            # Since it's a simple task, it routes to macro_brain which
            # calls _direct_llm → provider.chat()
            assert "routing" in data


# ===============================================================================
#  POST /brain/plan
# ===============================================================================


class TestGeneratePlan:
    """POST /brain/plan — generate a strategy plan."""

    def test_missing_goal_returns_400(self, client):
        r = client.post("/brain/plan", json={})
        assert r.status_code == 400
        assert r.json()["ok"] is False

    def test_empty_goal_returns_400(self, client):
        r = client.post("/brain/plan", json={"goal": ""})
        assert r.status_code == 400
        assert r.json()["ok"] is False

    def test_whitespace_goal_returns_400(self, client):
        r = client.post("/brain/plan", json={"goal": "   "})
        assert r.status_code == 400
        assert r.json()["ok"] is False

    def test_fallback_plan_without_provider(self, client):
        """When no LLM provider is available, Strategy Brain falls back."""
        r = client.post("/brain/plan", json={
            "goal": "Build a web application",
        })
        assert r.status_code == 200
        body = r.json()
        assert body["ok"] is True
        data = body["data"]
        assert "steps" in data
        assert len(data["steps"]) == 3  # fallback produces 3 steps
        assert "goal" in data

    def test_fallback_plan_structure(self, client):
        data = client.post("/brain/plan", json={
            "goal": "Build a web app",
        }).json()["data"]
        for step in data["steps"]:
            assert "id" in step
            assert "description" in step
            assert "agentType" in step
            assert "dependsOn" in step
            assert "isCritical" in step

    def test_fallback_plan_first_step_is_critical(self, client):
        data = client.post("/brain/plan", json={
            "goal": "Build a web app",
        }).json()["data"]
        assert data["steps"][0]["isCritical"] is True

    def test_plan_includes_cost_and_latency(self, client):
        data = client.post("/brain/plan", json={
            "goal": "Build a web app",
        }).json()["data"]
        assert "estimatedTotalCost" in data
        assert "estimatedTotalLatencyMs" in data
        assert "parallelGroups" in data
        assert data["estimatedTotalCost"] > 0
        assert data["estimatedTotalLatencyMs"] > 0

    def test_plan_with_max_steps(self, client):
        data = client.post("/brain/plan", json={
            "goal": "Build a web app",
            "maxSteps": 5,
        }).json()["data"]
        assert len(data["steps"]) >= 1

    def test_plan_with_mocked_provider(self, client):
        """Full flow with a mocked provider that returns structured JSON."""
        mock_plan = {
            "steps": [
                {
                    "id": "step_0",
                    "description": "Design the database schema",
                    "agent_type": "sector_brain",
                    "sector_brain_id": "coding",
                    "task_type": "code",
                    "depends_on": [],
                    "parallel_group": None,
                    "is_critical": True,
                    "context_hint": "Requirements analysis",
                },
                {
                    "id": "step_1",
                    "description": "Implement REST API endpoints",
                    "agent_type": "sector_brain",
                    "sector_brain_id": "coding",
                    "task_type": "code",
                    "depends_on": ["step_0"],
                    "parallel_group": None,
                    "is_critical": False,
                    "context_hint": "Database schema from step_0",
                },
            ]
        }

        import json
        from unittest.mock import MagicMock

        with patch("app.providers.router.ProviderRouter.get") as mock_get:
            mock_provider = AsyncMock()
            mock_provider.chat.return_value = {
                "choices": [{"message": {"content": json.dumps(mock_plan)}}]
            }
            # ProviderRouter.get_active_provider() is sync — use MagicMock
            mock_router = MagicMock()
            mock_router.get_active_provider.return_value = mock_provider
            mock_get.return_value = mock_router

            r = client.post("/brain/plan", json={
                "goal": "Build a REST API",
                "context": "User management system",
            })
            assert r.status_code == 200
            data = r.json()["data"]
            assert len(data["steps"]) == 2
            assert data["steps"][0]["id"] == "step_0"
            assert data["steps"][0]["isCritical"] is True
            assert data["goal"] == "Build a REST API"


# ===============================================================================
#  GET /brain/reputation
# ===============================================================================


class TestReputation:
    """GET /brain/reputation — agent reputation rankings."""

    def test_empty_rankings(self, client):
        r = client.get("/brain/reputation")
        assert r.status_code == 200
        data = r.json()["data"]
        assert data["rankings"] == []
        assert data["totalTracked"] == 0

    def test_rankings_with_data(self, client):
        _seed_reputation()
        data = client.get("/brain/reputation").json()["data"]
        assert len(data["rankings"]) == 5
        assert data["totalTracked"] == 5

    def test_rankings_sorted_by_trust_score(self, client):
        _seed_reputation()
        rankings = client.get("/brain/reputation").json()["data"]["rankings"]
        scores = [r["trustScore"] for r in rankings]
        assert scores == sorted(scores, reverse=True)

    def test_best_agent_is_coding(self, client):
        _seed_reputation()
        rankings = client.get("/brain/reputation").json()["data"]["rankings"]
        # Coding brain has 2 successful tasks → highest trust score
        assert rankings[0]["agentId"] == "sector_coding"

    def test_min_tasks_filter(self, client):
        _seed_reputation()
        # After seeding, each agent has 1 task, so minTasks=2 returns empty
        data = client.get("/brain/reputation?minTasks=2").json()["data"]
        assert len(data["rankings"]) == 0

    def test_agent_type_filter(self, client):
        _seed_reputation()
        data = client.get("/brain/reputation?agentType=sector_brain").json()["data"]
        for r in data["rankings"]:
            assert r["agentType"] == "sector_brain"

    def test_high_min_tasks_excludes_all(self, client):
        _seed_reputation()
        data = client.get("/brain/reputation?minTasks=99").json()["data"]
        assert data["rankings"] == []

    def test_record_includes_specializations(self, client):
        _seed_reputation()
        rankings = client.get("/brain/reputation").json()["data"]["rankings"]
        coding = next(r for r in rankings if r["agentId"] == "sector_coding")
        assert "specializations" in coding
        assert "code" in coding["specializations"]
        assert coding["specializations"]["code"] > 0


# ===============================================================================
#  GET /brain/routing
# ===============================================================================


class TestRoutingHistory:
    """GET /brain/routing — Smart Router history."""

    def test_empty_history(self, client):
        r = client.get("/brain/routing")
        assert r.status_code == 200
        data = r.json()["data"]
        assert data["routingHistory"] == []

    def test_history_with_data(self, client):
        _seed_routing()
        data = client.get("/brain/routing").json()["data"]
        assert len(data["routingHistory"]) == 3

    def test_history_limit(self, client):
        _seed_routing()
        data = client.get("/brain/routing?limit=2").json()["data"]
        assert len(data["routingHistory"]) == 2

    def test_history_entries_have_expected_fields(self, client):
        _seed_routing()
        entry = client.get("/brain/routing").json()["data"]["routingHistory"][0]
        assert "recommendedMode" in entry
        assert "complexity" in entry
        assert "taskType" in entry
        assert "confidence" in entry
        assert "suggestedAgents" in entry
        assert "reasoning" in entry

    def test_history_code_task_routes_to_coding(self, client):
        _seed_routing()
        history = client.get("/brain/routing").json()["data"]["routingHistory"]
        code_entry = next(h for h in history if h["taskType"] == "code")
        assert code_entry["recommendedMode"] == "coding"
        assert "coding" in code_entry["suggestedAgents"]


# ===============================================================================
#  POST /brain/sector/{id}
# ===============================================================================


class TestSectorBrain:
    """POST /brain/sector/{id} — directly invoke a sector brain."""

    def test_unknown_sector_returns_404(self, client):
        r = client.post("/brain/sector/nonexistent", json={"task": "Hello"})
        assert r.status_code == 404
        assert r.json()["ok"] is False

    def test_missing_task_returns_400(self, client):
        r = client.post("/brain/sector/coding", json={})
        assert r.status_code == 400
        assert r.json()["ok"] is False

    def test_empty_task_returns_400(self, client):
        r = client.post("/brain/sector/coding", json={"task": ""})
        assert r.status_code == 400
        assert r.json()["ok"] is False

    def test_valid_sector_returns_result_structure(self, client):
        """Even without a provider, returns a structured result with error info."""
        r = client.post("/brain/sector/coding", json={
            "task": "Sort an array in Python",
        })
        assert r.status_code == 200
        body = r.json()
        assert body["ok"] is True
        data = body["data"]
        assert data["sectorId"] == "coding"
        assert data["brainName"] == "Coding Brain"
        assert "result" in data
        assert "success" in data["result"]
        assert "error" in data["result"]

    def test_coding_brain_result(self, client):
        r = client.post("/brain/sector/coding", json={
            "task": "Write a sorting function",
        })
        data = r.json()["data"]
        assert data["sectorId"] == "coding"
        assert data["brainName"] == "Coding Brain"

    def test_research_brain_result(self, client):
        r = client.post("/brain/sector/research", json={
            "task": "Research AI",
        })
        assert r.status_code == 200
        data = r.json()["data"]
        assert data["sectorId"] == "research"

    def test_security_brain_result(self, client):
        r = client.post("/brain/sector/security", json={
            "task": "Check SQL injection",
        })
        assert r.status_code == 200
        data = r.json()["data"]
        assert data["sectorId"] == "security"

    def test_sector_tracks_reputation(self, client):
        client.post("/brain/sector/coding", json={
            "task": "Write code",
        })
        from app.brain.agent_reputation import AgentReputation
        records = AgentReputation.get().get_all_records()
        assert len(records) >= 1
        coding_record = next(r for r in records if r["agentId"] == "sector_coding")
        assert coding_record["totalTasks"] == 1

    def test_coding_brain_no_provider_returns_error(self, client):
        """When no provider is available, the brain returns error gracefully."""
        from unittest.mock import MagicMock

        with patch("app.providers.router.ProviderRouter.get") as mock_get:
            mock_router = MagicMock()
            mock_router.get_active_provider.return_value = None
            mock_get.return_value = mock_router

            r = client.post("/brain/sector/coding", json={
                "task": "Write code",
            })
            assert r.status_code == 200
            result = r.json()["data"]["result"]
            assert result["success"] is False
            assert result["error"] is not None
            assert "No AI provider available" in result["error"]

    def test_coding_brain_with_mocked_provider(self, client):
        """Full flow with a mocked provider returning a response."""
        from unittest.mock import MagicMock

        with patch("app.providers.router.ProviderRouter.get") as mock_get:
            mock_provider = AsyncMock()
            mock_provider.chat.return_value = {
                "choices": [{"message": {"content": "def sort(arr): return sorted(arr)"}}]
            }
            # ProviderRouter.get_active_provider() is sync — use MagicMock
            mock_router = MagicMock()
            mock_router.get_active_provider.return_value = mock_provider
            mock_get.return_value = mock_router

            r = client.post("/brain/sector/coding", json={
                "task": "Write a sort function in Python",
            })
            assert r.status_code == 200
            data = r.json()["data"]
            assert data["sectorId"] == "coding"
            result = data["result"]
            assert result["success"] is True
            assert "sort" in result["output"]

    def test_all_sector_brains_accept_requests(self, client):
        """Every registered sector brain accepts a POST with a task."""
        from app.brain.sector_brains import SECTOR_BRAIN_REGISTRY
        for sid in SECTOR_BRAIN_REGISTRY:
            r = client.post(f"/brain/sector/{sid}", json={
                "task": f"Test task for {sid}",
            })
            assert r.status_code == 200, f"Sector brain '{sid}' returned {r.status_code}"
            body = r.json()
            assert body["ok"] is True
            assert body["data"]["sectorId"] == sid
