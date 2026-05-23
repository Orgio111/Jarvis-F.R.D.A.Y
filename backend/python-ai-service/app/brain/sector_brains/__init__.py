"""
Sector Brains — Specialized cognitive layers reporting to the Macro Brain.

Each sector brain:
  - Has deep domain-specific reasoning
  - Can spawn execution agents
  - Reports confidence + results back to the Macro Brain
  - Maintains its own isolated context

Available sector brain types:
  - CodingBrain
  - ResearchBrain
  - DevOpsBrain
  - SecurityBrain
  - MemoryBrain
  - UIUXBrain
  - FinanceBrain
  - CreativeBrain
  - AutomationBrain
  - DataBrain
"""
from __future__ import annotations

from app.brain.sector_brains.base_sector_brain import BaseSectorBrain, SectorBrainResult

from app.brain.sector_brains.coding_brain import CodingBrain
from app.brain.sector_brains.research_brain import ResearchBrain
from app.brain.sector_brains.devops_brain import DevOpsBrain
from app.brain.sector_brains.security_brain import SecurityBrain
from app.brain.sector_brains.memory_brain import MemoryBrain
from app.brain.sector_brains.ui_ux_brain import UIUXBrain
from app.brain.sector_brains.finance_brain import FinanceBrain
from app.brain.sector_brains.creative_brain import CreativeBrain
from app.brain.sector_brains.automation_brain import AutomationBrain
from app.brain.sector_brains.data_brain import DataBrain

__all__ = [
    "BaseSectorBrain",
    "SectorBrainResult",
    "CodingBrain",
    "ResearchBrain",
    "DevOpsBrain",
    "SecurityBrain",
    "MemoryBrain",
    "UIUXBrain",
    "FinanceBrain",
    "CreativeBrain",
    "AutomationBrain",
    "DataBrain",
]

# Registry: sector_id → sector brain class
SECTOR_BRAIN_REGISTRY: dict[str, type[BaseSectorBrain]] = {
    "coding": CodingBrain,
    "research": ResearchBrain,
    "devops": DevOpsBrain,
    "security": SecurityBrain,
    "memory_brain": MemoryBrain,
    "ui_ux": UIUXBrain,
    "finance": FinanceBrain,
    "creative": CreativeBrain,
    "automation": AutomationBrain,
    "data": DataBrain,
}


def get_sector_brain(sector_id: str) -> type[BaseSectorBrain] | None:
    """Look up a sector brain class by its identifier."""
    return SECTOR_BRAIN_REGISTRY.get(sector_id)


def list_sector_brains() -> list[dict[str, str]]:
    """Return metadata about all registered sector brains."""
    return [
        {
            "id": sid,
            "name": cls.get_brain_name(),
            "description": cls.get_brain_description(),
            "capabilities": cls.get_capabilities(),
        }
        for sid, cls in SECTOR_BRAIN_REGISTRY.items()
    ]
