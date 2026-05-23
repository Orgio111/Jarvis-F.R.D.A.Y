"""Unit tests for Sector Brains.

Tests cover:
  - All 10 sector brain class metadata (SECTOR_ID, BRAIN_NAME, DESCRIPTION, CAPABILITIES)
  - get_system_prompt returns non-empty string for each brain
  - SECTOR_BRAIN_REGISTRY contains all brains
  - get_sector_brain lookup
  - list_sector_brains returns metadata
  - SectorBrainResult dataclass defaults and construction
  - Each brain's system prompt includes relevant domain keywords
"""
from __future__ import annotations

import pytest

from app.brain.sector_brains import (
    BaseSectorBrain,
    SectorBrainResult,
    CodingBrain,
    ResearchBrain,
    DevOpsBrain,
    SecurityBrain,
    MemoryBrain,
    UIUXBrain,
    FinanceBrain,
    CreativeBrain,
    AutomationBrain,
    DataBrain,
    SECTOR_BRAIN_REGISTRY,
    get_sector_brain,
    list_sector_brains,
)


# ── SectorBrainResult ─────────────────────────────────────────────────────────


class TestSectorBrainResult:
    def test_default_values(self):
        r = SectorBrainResult(success=True, output="done")
        assert r.success is True
        assert r.output == "done"
        assert r.confidence == 0.0
        assert r.reasoning == ""
        assert r.suggestions == []
        assert r.actions_taken == []
        assert r.elapsed_ms == 0.0
        assert r.error is None
        assert r.brain_id == ""
        assert r.brain_name == ""

    def test_with_all_fields(self):
        r = SectorBrainResult(
            success=True,
            output="Analysis complete",
            confidence=0.95,
            reasoning="Processed via deep analysis",
            suggestions=["Check imports", "Add validation"],
            actions_taken=[{"action": "analyzed", "target": "codebase"}],
            elapsed_ms=1500.5,
            error=None,
            brain_id="coding",
            brain_name="Coding Brain",
        )
        assert r.confidence == 0.95
        assert len(r.suggestions) == 2
        assert r.brain_id == "coding"

    def test_error_result(self):
        r = SectorBrainResult(success=False, output="", error="Provider unavailable")
        assert r.success is False
        assert r.error == "Provider unavailable"


# ── BaseSectorBrain (abstract) ────────────────────────────────────────────────


class TestBaseSectorBrain:
    def test_base_class_is_abstract(self):
        with pytest.raises(TypeError):
            BaseSectorBrain()

    def test_get_brain_id_returns_class_variable(self):
        assert CodingBrain.get_brain_id() == "coding"


# ── Individual Brain Metadata ─────────────────────────────────────────────────


BRAIN_PARAMS = [
    (CodingBrain, "coding", "Coding Brain"),
    (ResearchBrain, "research", "Research Brain"),
    (DevOpsBrain, "devops", "DevOps Brain"),
    (SecurityBrain, "security", "Security Brain"),
    (MemoryBrain, "memory_brain", "Memory Brain"),
    (UIUXBrain, "ui_ux", "UI/UX Brain"),
    (FinanceBrain, "finance", "Finance Brain"),
    (CreativeBrain, "creative", "Creative Brain"),
    (AutomationBrain, "automation", "Automation Brain"),
    (DataBrain, "data", "Data Brain"),
]


class TestBrainMetadata:
    @pytest.mark.parametrize("cls,expected_id,expected_name", BRAIN_PARAMS)
    def test_sector_id(self, cls, expected_id, expected_name):
        assert cls.SECTOR_ID == expected_id

    @pytest.mark.parametrize("cls,expected_id,expected_name", BRAIN_PARAMS)
    def test_brain_name(self, cls, expected_id, expected_name):
        assert cls.BRAIN_NAME == expected_name

    @pytest.mark.parametrize("cls,expected_id,expected_name", BRAIN_PARAMS)
    def test_description_not_empty(self, cls, expected_id, expected_name):
        assert cls.DESCRIPTION, f"{expected_name} has empty description"

    @pytest.mark.parametrize("cls,expected_id,expected_name", BRAIN_PARAMS)
    def test_capabilities_not_empty(self, cls, expected_id, expected_name):
        assert cls.CAPABILITIES, f"{expected_name} has empty capabilities list"

    @pytest.mark.parametrize("cls,expected_id,expected_name", BRAIN_PARAMS)
    def test_get_brain_id_classmethod(self, cls, expected_id, expected_name):
        assert cls.get_brain_id() == expected_id

    @pytest.mark.parametrize("cls,expected_id,expected_name", BRAIN_PARAMS)
    def test_get_brain_name_classmethod(self, cls, expected_id, expected_name):
        assert cls.get_brain_name() == expected_name


# ── System Prompts ────────────────────────────────────────────────────────────


class TestSystemPrompts:
    @pytest.mark.parametrize("cls,expected_id,expected_name", BRAIN_PARAMS)
    def test_system_prompt_returns_string(self, cls, expected_id, expected_name):
        instance = cls()
        prompt = instance.get_system_prompt()
        assert isinstance(prompt, str)
        assert len(prompt) > 50

    @pytest.mark.parametrize("cls,expected_id,expected_name", BRAIN_PARAMS)
    def test_system_prompt_with_context(self, cls, expected_id, expected_name):
        instance = cls()
        prompt = instance.get_system_prompt(context="User is building a web app")
        assert isinstance(prompt, str)
        assert "web app" in prompt

    def test_coding_brain_prompt_includes_domain_keywords(self):
        brain = CodingBrain()
        prompt = brain.get_system_prompt()
        assert "coding" in prompt.lower() or "code" in prompt.lower() or "software" in prompt.lower()

    def test_security_brain_prompt_includes_security_keywords(self):
        brain = SecurityBrain()
        prompt = brain.get_system_prompt()
        assert "security" in prompt.lower() or "vulnerability" in prompt.lower()

    def test_finance_brain_prompt_includes_finance_keywords(self):
        brain = FinanceBrain()
        prompt = brain.get_system_prompt()
        assert "finance" in prompt.lower() or "cost" in prompt.lower() or "budget" in prompt.lower()

    def test_research_brain_prompt_includes_research_keywords(self):
        brain = ResearchBrain()
        prompt = brain.get_system_prompt()
        assert "research" in prompt.lower() or "sources" in prompt.lower() or "information" in prompt.lower()

    def test_memory_brain_prompt_includes_memory_keywords(self):
        brain = MemoryBrain()
        prompt = brain.get_system_prompt()
        assert "memory" in prompt.lower() or "store" in prompt.lower() or "retrieval" in prompt.lower()


# ── Registry ──────────────────────────────────────────────────────────────────


class TestRegistry:
    def test_registry_contains_all_brains(self):
        assert len(SECTOR_BRAIN_REGISTRY) == 10
        assert "coding" in SECTOR_BRAIN_REGISTRY
        assert "research" in SECTOR_BRAIN_REGISTRY
        assert "devops" in SECTOR_BRAIN_REGISTRY
        assert "security" in SECTOR_BRAIN_REGISTRY
        assert "memory_brain" in SECTOR_BRAIN_REGISTRY
        assert "ui_ux" in SECTOR_BRAIN_REGISTRY
        assert "finance" in SECTOR_BRAIN_REGISTRY
        assert "creative" in SECTOR_BRAIN_REGISTRY
        assert "automation" in SECTOR_BRAIN_REGISTRY
        assert "data" in SECTOR_BRAIN_REGISTRY

    def test_registry_values_are_brain_classes(self):
        for brain_cls in SECTOR_BRAIN_REGISTRY.values():
            assert issubclass(brain_cls, BaseSectorBrain)

    def test_get_sector_brain_returns_class(self):
        cls = get_sector_brain("coding")
        assert cls is CodingBrain

    @pytest.mark.parametrize("sector_id,expected_cls", [
        ("coding", CodingBrain),
        ("research", ResearchBrain),
        ("devops", DevOpsBrain),
        ("security", SecurityBrain),
        ("memory_brain", MemoryBrain),
        ("ui_ux", UIUXBrain),
        ("finance", FinanceBrain),
        ("creative", CreativeBrain),
        ("automation", AutomationBrain),
        ("data", DataBrain),
    ])
    def test_get_sector_brain_all(self, sector_id, expected_cls):
        assert get_sector_brain(sector_id) is expected_cls

    def test_get_sector_brain_returns_none_for_unknown(self):
        assert get_sector_brain("nonexistent") is None

    def test_list_sector_brains_returns_all(self):
        brains = list_sector_brains()
        assert len(brains) == 10
        for b in brains:
            assert "id" in b
            assert "name" in b
            assert "description" in b
            assert "capabilities" in b

    def test_list_sector_brains_entries_have_ids(self):
        brains = list_sector_brains()
        ids = {b["id"] for b in brains}
        assert ids == set(SECTOR_BRAIN_REGISTRY.keys())


# ── SectorBrain Instance ──────────────────────────────────────────────────────


class TestBrainInstance:
    def test_can_instantiate_all_brains(self):
        for cls in SECTOR_BRAIN_REGISTRY.values():
            instance = cls()
            assert instance.get_system_prompt()
            assert instance.SECTOR_ID is not None
            assert instance.BRAIN_NAME is not None

    def test_each_brain_has_unique_id(self):
        ids = [cls.SECTOR_ID for cls in SECTOR_BRAIN_REGISTRY.values()]
        assert len(ids) == len(set(ids))

    def test_each_brain_has_unique_name(self):
        names = [cls.BRAIN_NAME for cls in SECTOR_BRAIN_REGISTRY.values()]
        assert len(names) == len(set(names))
