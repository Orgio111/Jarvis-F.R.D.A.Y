"""
JARVIS Swarm Manager — Distributed autonomous swarm intelligence.

A swarm is a fully autonomous cluster of specialized cognitive agents that
collaborate, communicate, and coordinate to execute complex tasks.

Architecture:
  SwarmManager (controller)
      ├── Swarm: ResearchSwarm, CodingSwarm, PlannerSwarm, SecuritySwarm,
      │          BrowserSwarm, DevOpsSwarm, VisionSwarm, VoiceSwarm
      ├── SwarmAgent (individual agent within a swarm)
      └── SwarmProtocol (inter-swarm communication + coordination)
"""

from swarm_manager.models import (
    SwarmSpec,
    SwarmAgent,
    SwarmMetrics,
    SwarmState,
    SwarmRole,
    AgentCapability,
    SwarmProtocolMessage,
    SwarmHealthReport,
)
from swarm_manager.manager import SwarmManager

__all__ = [
    "SwarmManager",
    "SwarmSpec",
    "SwarmAgent",
    "SwarmMetrics",
    "SwarmState",
    "SwarmRole",
    "AgentCapability",
    "SwarmProtocolMessage",
    "SwarmHealthReport",
]
