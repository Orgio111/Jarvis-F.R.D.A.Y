"""
Swarm Manager Service — backend integration for the distributed agent swarm system.

Integrates the Swarm Manager package with the JARVIS backend:
  - Initializes swarms on startup (one per configured role)
  - Routes brain-level tasks to swarms dynamically
  - Reports swarm health and metrics
  - Auto-scales swarms based on load
"""

from __future__ import annotations

import time
from typing import Any

from app.core.config import Settings
from app.core.logging import get_logger

# Optional import — the swarm-manager package may not be installed
# in all deployment targets (e.g. Docker base image).
try:
    from swarm_manager.manager import SwarmManager
    from swarm_manager.models import (
        AgentCapability,
        SwarmRole,
        SwarmSpec,
    )
    _SWARM_MANAGER_AVAILABLE = True
except ImportError:
    SwarmManager = None  # type: ignore
    SwarmRole = None  # type: ignore
    SwarmSpec = None  # type: ignore
    AgentCapability = None  # type: ignore
    _SWARM_MANAGER_AVAILABLE = False
    import logging
    logging.getLogger(__name__).warning("swarm_manager_package_not_available")

logger = get_logger(__name__)


class SwarmManagerService:
    """
    Wraps SwarmManager for the JARVIS backend.

    On initialize(), spawns the default set of swarms that match the
    sector brain architecture: research, coding, planner, security,
    browser, devops, vision, voice, memory, and general-purpose.

    If the swarm-manager package is not installed, the service will
    be unavailable (all methods return empty/default results).
    """

    _instance: SwarmManagerService | None = None

    def __init__(self, settings: Settings):
        self._settings = settings
        self._swarm_ids: dict[str, str] = {}  # role → swarm_id
        self._initialized = False
        if _SWARM_MANAGER_AVAILABLE:
            self._manager = SwarmManager.initialize()
        else:
            self._manager = None
            logger.warning("swarm_manager_unavailable", reason="package_not_installed")

    @classmethod
    def initialize(cls, settings: Settings) -> SwarmManagerService:
        cls._instance = cls(settings)
        if _SWARM_MANAGER_AVAILABLE:
            cls._instance._bootstrap()
        return cls._instance

    @classmethod
    def get(cls) -> SwarmManagerService:
        if cls._instance is None:
            raise RuntimeError("SwarmManagerService not initialized")
        return cls._instance

    def _bootstrap(self) -> None:
        """Spawn default swarms matching the sector brain architecture."""
        if not _SWARM_MANAGER_AVAILABLE:
            self._initialized = True
            return
        roles = [
            SwarmRole.RESEARCH,
            SwarmRole.CODING,
            SwarmRole.PLANNER,
            SwarmRole.SECURITY,
            SwarmRole.BROWSER,
            SwarmRole.DEVOPS,
            SwarmRole.VISION,
            SwarmRole.VOICE,
        ]

        if self._settings.app_env == "development":
            # In development, spawn reduced swarms
            roles = [SwarmRole.GENERAL, SwarmRole.RESEARCH, SwarmRole.CODING]

        for role in roles:
            spec = SwarmSpec.default_for_role(role)
            swarm_id = self._manager.spawn_swarm(spec)
            self._swarm_ids[role.value] = swarm_id
            logger.info("swarm_spawned", role=role.value, swarm_id=swarm_id, agents=spec.initial_agents)

        self._initialized = True
        logger.info("swarm_manager_initialized", swarm_count=len(self._swarm_ids))

    def route_brain_task(self, task: str, task_type: str = "general") -> dict[str, Any]:
        """
        Route a brain-level task to the appropriate swarm.

        Maps task types to swarm roles similar to SmartRouter's routing.
        """
        role_map = {
            "code": SwarmRole.CODING,
            "research": SwarmRole.RESEARCH,
            "planning": SwarmRole.PLANNER,
            "security": SwarmRole.SECURITY,
            "browser": SwarmRole.BROWSER,
            "devops": SwarmRole.DEVOPS,
            "vision": SwarmRole.VISION,
            "voice": SwarmRole.VOICE,
        }

        role = role_map.get(task_type, SwarmRole.GENERAL)
        swarm_id = self._swarm_ids.get(role.value)

        if swarm_id:
            return {
                "swarmId": swarm_id,
                "role": role.value,
                "available": swarm_id in self._manager._swarms,
            }

        # Fallback: let the manager decide
        return self._manager.route_task(task)

    def assign_to_swarm(self, swarm_id: str, agent_id: str, task_id: str) -> bool:
        """Assign a task to a specific agent within a swarm."""
        return self._manager.assign_task(swarm_id, agent_id, task_id)

    def complete_in_swarm(self, swarm_id: str, agent_id: str, success: bool, latency_ms: float, confidence: float = 0.0) -> None:
        """Mark a task as completed in a swarm."""
        self._manager.complete_task(swarm_id, agent_id, success, latency_ms, confidence)

    def get_swarm(self, swarm_id: str) -> dict[str, Any] | None:
        return self._manager.get_swarm(swarm_id)

    def list_swarms(self) -> list[dict[str, Any]]:
        return self._manager.list_swarms()

    def health_check_all(self) -> list[dict]:
        return self._manager.health_check_all()

    def get_status(self) -> dict[str, Any]:
        status = self._manager.get_status()
        status.update({
            "initialized": self._initialized,
            "swarmRoles": list(self._swarm_ids.keys()),
        })
        return status

    def spawn_swarm(self, role: str, min_agents: int = 1, max_agents: int = 3) -> dict[str, Any]:
        """Spawn a custom swarm by role name."""
        try:
            role_enum = SwarmRole(role)
        except ValueError:
            return {"success": False, "error": f"Invalid role: {role}"}

        spec = SwarmSpec.default_for_role(role_enum)
        spec.min_agents = min_agents
        spec.max_agents = max_agents

        swarm_id = self._manager.spawn_swarm(spec)
        self._swarm_ids[role] = swarm_id

        logger.info("custom_swarm_spawned", role=role, swarm_id=swarm_id)
        return {"success": True, "swarmId": swarm_id, "role": role, "agentCount": spec.initial_agents}

    def terminate_swarm(self, swarm_id: str) -> bool:
        """Terminate a swarm."""
        # Remove from our tracking
        for role, sid in list(self._swarm_ids.items()):
            if sid == swarm_id:
                del self._swarm_ids[role]
                break
        return self._manager.terminate_swarm(swarm_id)

    def auto_scale_all(self) -> list[dict[str, Any]]:
        """Run auto-scaling on all swarms."""
        results = []
        for swarm_id in self._manager._swarms:
            result = self._manager.auto_scale(swarm_id)
            if result["action"] != "none":
                results.append({"swarmId": swarm_id, **result})
        return results

    def heal_all(self) -> list[dict[str, Any]]:
        """Run self-healing on all degraded swarms."""
        results = []
        for swarm_id in self._manager._swarms:
            result = self._manager.heal_swarm(swarm_id)
            if result["action"] != "none":
                results.append({"swarmId": swarm_id, **result})
        return results
