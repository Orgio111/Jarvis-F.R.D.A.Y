"""
J.A.R.V.I.S. Brain Architecture
──────────────────────────────────
Macro Brain (CEO) → Sector Brains (specialists) → Strategy Brain (planner)
                 → Execution Brain (doer)
                 → Smart Router (model selector)
                 → Agent Reputation (performance tracker)
"""
from __future__ import annotations

from app.brain.macro_brain import MacroBrain
from app.brain.strategy_brain import StrategyBrain
from app.brain.smart_router import SmartRouter
from app.brain.agent_reputation import AgentReputation

__all__ = [
    "MacroBrain",
    "StrategyBrain",
    "SmartRouter",
    "AgentReputation",
]
