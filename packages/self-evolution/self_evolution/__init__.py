"""
JARVIS Self-Evolution Engine — Continuous system improvement through mutation, scoring, and reinforcement.

The evolution loop:
  1. EVALUATE  — analyze execution quality and outcomes
  2. SCORE     — assign numerical scores across dimensions
  3. MUTATE    — generate strategy/prompt/routing mutations
  4. RETRY     — re-execute with mutations and compare
  5. REINFORCE — strengthen successful patterns, weaken failures

This engine works across:
  - Prompt strategies (system prompts, instructions)
  - Routing decisions (model selection, agent assignment)
  - Workflow patterns (step ordering, parallelization)
  - Agent configurations (capabilities, thresholds, priority)
"""

from self_evolution.engine import EvolutionEngine, MutationType, EvolutionScore, EvolutionTrial

__all__ = [
    "EvolutionEngine",
    "MutationType",
    "EvolutionScore",
    "EvolutionTrial",
]
