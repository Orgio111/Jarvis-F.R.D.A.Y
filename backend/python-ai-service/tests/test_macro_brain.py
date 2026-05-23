"""Unit tests for Macro Brain.

Tests cover:
  - Singleton pattern and initialization
  - get_brain creates and caches sector brain instances
  - get_status returns complete system status
  - _brain_result_to_dict serialization
  - Reputation tracking after processing
  - _direct_llm fallback (with mocked provider)
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.brain.macro_brain import MacroBrain
from app.brain.sector_brains import (
    BaseSectorBrain,
    SectorBrainResult,
    SECTOR_BRAIN_REGISTRY,
)


# ── MacroBrain (singleton + initialization) ───────────────────────────────────


class TestMacroBrainInit:
    def test_singleton(self):
        MacroBrain._instance = None
        a = MacroBrain.get()
        b = MacroBrain.get()
        assert a is b

    def test_initialize_creates_new_instance(self):
        MacroBrain._instance = None
        inst = MacroBrain.initialize()
        assert MacroBrain.get() is inst

    def test_get_returns_initialized_instance(self):
        MacroBrain._instance = None
        inst = MacroBrain.initialize()
        assert MacroBrain.get() is inst


# ── get_brain ─────────────────────────────────────────────────────────────────


class TestGetBrain:
    def setup_method(self):
        MacroBrain._instance = None
        self.macro = MacroBrain()

    def test_get_brain_returns_sector_brain_for_valid_id(self):
        brain = self.macro.get_brain("coding")
        assert brain is not None
        assert isinstance(brain, BaseSectorBrain)
        assert brain.SECTOR_ID == "coding"

    def test_get_brain_returns_none_for_invalid_id(self):
        brain = self.macro.get_brain("nonexistent")
        assert brain is None

    def test_get_brain_caches_instances(self):
        brain1 = self.macro.get_brain("security")
        brain2 = self.macro.get_brain("security")
        assert brain1 is brain2

    def test_get_brain_creates_new_instance_per_id(self):
        coding = self.macro.get_brain("coding")
        research = self.macro.get_brain("research")
        assert coding is not research

    def test_get_brain_works_for_all_registered(self):
        for sector_id in SECTOR_BRAIN_REGISTRY:
            brain = self.macro.get_brain(sector_id)
            assert brain is not None, f"Failed to get brain for {sector_id}"
            assert brain.SECTOR_ID == sector_id


# ── Serialization ─────────────────────────────────────────────────────────────


class TestBrainResultToDict:
    def setup_method(self):
        MacroBrain._instance = None
        self.macro = MacroBrain()

    def test_converts_success_result(self):
        br = SectorBrainResult(
            success=True,
            output="Test output that is long enough",
            confidence=0.95,
            reasoning="Because analysis",
            suggestions=["Fix A", "Fix B"],
            actions_taken=[{"action": "analyzed"}],
            elapsed_ms=1234.5,
            brain_id="coding",
            brain_name="Coding Brain",
        )
        d = self.macro._brain_result_to_dict(br)
        assert d["success"] is True
        assert d["confidence"] == 0.95
        assert d["brainId"] == "coding"
        assert d["brainName"] == "Coding Brain"
        assert len(d["suggestions"]) == 2

    def test_converts_error_result(self):
        br = SectorBrainResult(success=False, output="", error="Something broke")
        d = self.macro._brain_result_to_dict(br)
        assert d["success"] is False
        assert d["error"] == "Something broke"
        assert d["output"] == ""


# ── get_status ────────────────────────────────────────────────────────────────


class TestGetStatus:
    def setup_method(self):
        MacroBrain._instance = None
        self.macro = MacroBrain()

    def test_status_contains_macro_brain(self):
        status = self.macro.get_status()
        assert "macroBrain" in status
        assert status["macroBrain"]["initialized"] is True

    def test_status_contains_sector_brains(self):
        status = self.macro.get_status()
        assert "sectorBrains" in status
        assert len(status["sectorBrains"]) == 10

    def test_status_contains_reputation(self):
        status = self.macro.get_status()
        assert "reputation" in status

    def test_status_contains_strategy_brain(self):
        status = self.macro.get_status()
        assert status["strategyBrain"]["available"] is True

    def test_status_contains_smart_router(self):
        status = self.macro.get_status()
        assert status["smartRouter"]["available"] is True

    def test_status_sector_brain_count_tracks_instantiated(self):
        self.macro.get_brain("coding")
        self.macro.get_brain("research")
        status = self.macro.get_status()
        assert status["macroBrain"]["sectorBrainCount"] == 2
        assert status["macroBrain"]["availableSectors"] == 10


# ── Direct LLM (mocked) ──────────────────────────────────────────────────────


class TestDirectLLM:
    @pytest.mark.asyncio
    async def test_direct_llm_with_mock_provider(self):
        MacroBrain._instance = None
        macro = MacroBrain()

        mock_provider = AsyncMock()
        mock_provider.chat.return_value = {
            "choices": [{"message": {"content": "Hello, JARVIS here!"}}],
        }

        with patch("app.providers.router.ProviderRouter") as MockPR:
            mock_pr = MagicMock()
            mock_pr.get_active_provider.return_value = mock_provider
            MockPR.get.return_value = mock_pr

            result = await macro._direct_llm("Say hello", "Context: test", 1024)

        assert result["success"] is True
        assert result["output"] == "Hello, JARVIS here!"
        assert result["confidence"] == 0.8

    @pytest.mark.asyncio
    async def test_direct_llm_no_provider(self):
        MacroBrain._instance = None
        macro = MacroBrain()

        with patch("app.providers.router.ProviderRouter") as MockPR:
            mock_pr = MagicMock()
            mock_pr.get_active_provider.return_value = None
            MockPR.get.return_value = mock_pr

            result = await macro._direct_llm("Hello", "", 1024)

        assert result["success"] is False
        assert result["error"] == "No provider available"


# ── Process (mocked provider) ─────────────────────────────────────────────────


class TestProcess:
    @pytest.mark.asyncio
    async def test_process_with_sector_brain(self):
        """Process should route to sector brain when sector_brain_id is given."""
        MacroBrain._instance = None
        macro = MacroBrain()

        # Use a real sector brain — process() will fail because there's no provider,
        # but we can check the structure of the result
        # Instead, let's mock the brain's process method
        mock_brain = AsyncMock(spec=BaseSectorBrain)
        mock_brain.process.return_value = SectorBrainResult(
            success=True,
            output="Brain processed this",
            confidence=0.92,
            brain_id="coding",
            brain_name="Coding Brain",
        )

        # Replace the brain in the cache
        macro._brain_instances["coding"] = mock_brain

        result = await macro.process(
            task="Write code",
            task_type="code",
            sector_brain_id="coding",
        )

        assert result["success"] is True
        assert result["output"] == "Brain processed this"
        assert result["confidence"] == 0.92
        assert result["taskType"] == "code"
        assert len(result["brainResults"]) == 1
        assert result["brainResults"][0]["sector"] == "coding"

    @pytest.mark.asyncio
    async def test_process_unknown_sector_brain(self):
        """Process should fall back to direct LLM for unknown sector brain IDs."""
        MacroBrain._instance = None
        macro = MacroBrain()

        mock_provider = AsyncMock()
        mock_provider.chat.return_value = {
            "choices": [{"message": {"content": "Fallback response"}}],
        }

        with patch("app.providers.router.ProviderRouter") as MockPR:
            mock_pr = MagicMock()
            mock_pr.get_active_provider.return_value = mock_provider
            MockPR.get.return_value = mock_pr

            result = await macro.process(
                task="Do something",
                task_type="general",
                sector_brain_id="nonexistent_brain",
            )

        # Should still succeed via fallback
        assert result["success"] is True
        assert result["output"] == "Fallback response"

    @pytest.mark.asyncio
    async def test_process_tracks_reputation(self):
        """Process should record reputation after execution."""
        MacroBrain._instance = None
        macro = MacroBrain()

        mock_brain = AsyncMock(spec=BaseSectorBrain)
        mock_brain.process.return_value = SectorBrainResult(
            success=True, output="OK", confidence=0.8,
            brain_id="research", brain_name="Research Brain",
        )
        macro._brain_instances["research"] = mock_brain

        result = await macro.process(
            task="Research topic",
            task_type="research",
            sector_brain_id="research",
        )

        # Check reputation was recorded
        rep_record = macro._reputation.get_record("sector_research")
        assert rep_record is not None
        assert rep_record["totalTasks"] == 1
        assert rep_record["successfulTasks"] == 1

    @pytest.mark.asyncio
    async def test_process_returns_routing_info(self):
        MacroBrain._instance = None
        macro = MacroBrain()

        mock_brain = AsyncMock(spec=BaseSectorBrain)
        mock_brain.process.return_value = SectorBrainResult(
            success=True, output="Result", confidence=0.9,
            brain_id="data", brain_name="Data Brain",
        )
        macro._brain_instances["data"] = mock_brain

        result = await macro.process(
            task="Analyze data",
            task_type="analysis",
            sector_brain_id="data",
            preferred_mode="smart",
        )

        assert "routing" in result
        assert result["routing"]["recommendedMode"] == "smart"
        assert result["routing"]["taskType"] == "analysis"
        assert result["elapsedMs"] > 0

    @pytest.mark.asyncio
    async def test_process_simple_task_without_sector_brain(self):
        """Simple tasks should go through direct LLM when no sector brain specified."""
        MacroBrain._instance = None
        macro = MacroBrain()

        mock_provider = AsyncMock()
        mock_provider.chat.return_value = {
            "choices": [{"message": {"content": "Simple response"}}],
        }

        with patch("app.providers.router.ProviderRouter") as MockPR:
            mock_pr = MagicMock()
            mock_pr.get_active_provider.return_value = mock_provider
            MockPR.get.return_value = mock_pr

            result = await macro.process(task="Simple hello", task_type="general")

        assert result["success"] is True
        assert result["output"] == "Simple response"
        # Should have no brainResults (direct LLM path)
        assert len(result["brainResults"]) == 0
