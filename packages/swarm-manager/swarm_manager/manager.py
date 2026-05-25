"""
SwarmManager — distributed autonomous swarm intelligence controller.

Capabilities:
  - Spawn/kill swarms and individual agents
  - Auto-scale based on utilization thresholds
  - Route tasks to appropriate swarms
  - Merge swarms for collaborative tasks
  - Health monitoring and self-healing
  - Inter-swarm protocol messaging
  - Performance tracking and optimization
"""

from __future__ import annotations

import time
from collections import defaultdict
from typing import Any
from uuid import uuid4

from swarm_manager.models import (
    AgentCapability,
    SwarmAgent,
    SwarmHealthReport,
    SwarmMetrics,
    SwarmProtocolMessage,
    SwarmRole,
    SwarmSpec,
    SwarmState,
)


class SwarmManager:
    """
    Central controller for all agent swarms.

    Manages the full lifecycle of swarms:
      PENDING → SPAWNING → ACTIVE/IDLE → SCALING → TERMINATING → TERMINATED

    Provides:
      - CRUD operations for swarms
      - Auto-scaling based on utilization
      - Task routing to best-fit swarm
      - Health monitoring
      - Inter-swarm communication
    """

    _instance: SwarmManager | None = None

    def __init__(self):
        self._swarms: dict[str, SwarmSpec] = {}
        self._agents: dict[str, list[SwarmAgent]] = defaultdict(list)
        self._metrics: dict[str, SwarmMetrics] = {}
        self._message_queue: list[SwarmProtocolMessage] = []
        self._max_messages = 1000

    @classmethod
    def initialize(cls) -> SwarmManager:
        cls._instance = cls()
        return cls._instance

    @classmethod
    def get(cls) -> SwarmManager:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    # ─── Swarm Lifecycle ──────────────────────────────────────────────────────

    def spawn_swarm(self, spec: SwarmSpec | None = None, role: SwarmRole | None = None) -> str:
        """
        Spawn a new swarm with the given specification or role.

        Returns the swarm ID.
        """
        if spec is None and role is None:
            role = SwarmRole.GENERAL
        if spec is None:
            spec = SwarmSpec.default_for_role(role)  # type: ignore

        swarm_id = f"swarm_{uuid4().hex[:10]}"
        self._swarms[swarm_id] = spec

        # Spawn initial agents
        agents: list[SwarmAgent] = []
        for _ in range(spec.initial_agents):
            agent = SwarmAgent(
                swarm_role=spec.role,
                capabilities=spec.capabilities,
                state=SwarmState.ACTIVE,
                spawned_at=time.time(),
                last_active_at=time.time(),
            )
            agents.append(agent)

        self._agents[swarm_id] = agents
        self._metrics[swarm_id] = SwarmMetrics(
            swarm_id=swarm_id,
            role=spec.role.value,
            agent_count=len(agents),
            active_agents=len(agents),
            uptime_seconds=0.0,
        )

        return swarm_id

    def terminate_swarm(self, swarm_id: str) -> bool:
        """Terminate a swarm and all its agents."""
        if swarm_id not in self._swarms:
            return False

        for agent in self._agents.get(swarm_id, []):
            agent.state = SwarmState.TERMINATED

        self._swarms.pop(swarm_id)
        if swarm_id in self._agents:
            del self._agents[swarm_id]
        if swarm_id in self._metrics:
            del self._metrics[swarm_id]

        return True

    def spawn_agents(self, swarm_id: str, count: int = 1) -> list[SwarmAgent]:
        """Add more agents to an existing swarm."""
        if swarm_id not in self._swarms:
            return []

        spec = self._swarms[swarm_id]
        current = self._agents[swarm_id]
        max_agents = spec.max_agents
        available = max_agents - len(current)

        if available <= 0:
            return []

        actual_count = min(count, available)
        new_agents: list[SwarmAgent] = []
        for _ in range(actual_count):
            agent = SwarmAgent(
                swarm_role=spec.role,
                capabilities=spec.capabilities,
                state=SwarmState.SPAWNING,
                spawned_at=time.time(),
            )
            new_agents.append(agent)

        current.extend(new_agents)
        self._update_metrics(swarm_id)
        return new_agents

    def kill_agents(self, swarm_id: str, count: int = 1) -> int:
        """Remove idle agents from a swarm. Returns number actually removed."""
        if swarm_id not in self._agents:
            return 0

        agents = self._agents[swarm_id]
        spec = self._swarms.get(swarm_id)
        min_agents = spec.min_agents if spec else 1

        # Only kill idle agents
        idle = [a for a in agents if a.state == SwarmState.IDLE]
        removable = len(agents) - min_agents
        actual_count = min(count, len(idle), removable)

        if actual_count <= 0:
            return 0

        killed = 0
        for agent in idle[:actual_count]:
            agent.state = SwarmState.TERMINATED
            killed += 1

        self._agents[swarm_id] = [a for a in agents if a.state != SwarmState.TERMINATED]
        self._update_metrics(swarm_id)
        return killed

    # ─── Task Routing ─────────────────────────────────────────────────────────

    def route_task(self, task: str, required_capabilities: list[AgentCapability] | None = None) -> dict[str, Any]:
        """
        Find the best swarm for a task based on role matching and availability.

        Returns routing decision with swarm_id, agent_id, and confidence.
        """
        if not self._swarms:
            return {"swarmId": None, "agentId": None, "confidence": 0.0, "reason": "No swarms available"}

        candidates: list[dict[str, Any]] = []

        for swarm_id, spec in self._swarms.items():
            agents = self._agents.get(swarm_id, [])
            active = [a for a in agents if a.state == SwarmState.ACTIVE or a.state == SwarmState.IDLE]
            if not active:
                continue

            # Score based on capability match
            score = 0.0
            if required_capabilities:
                swarm_caps = set(spec.capabilities)
                required = set(required_capabilities)
                if required.issubset(swarm_caps):
                    score = 1.0
                elif swarm_caps & required:
                    score = len(swarm_caps & required) / len(required)
                else:
                    continue
            else:
                score = 0.5

            # Boost by agent availability
            idle_count = len([a for a in active if a.state == SwarmState.IDLE])
            availability_boost = min(idle_count / max(spec.max_agents, 1), 1.0) * 0.3
            score += availability_boost

            # Boost by success rate
            metrics = self._metrics.get(swarm_id)
            if metrics and metrics.avg_success_rate > 0:
                score += metrics.avg_success_rate * 0.2

            # Pick best agent
            best_agent = max(active, key=lambda a: a.confidence_score)

            candidates.append({
                "swarmId": swarm_id,
                "agentId": best_agent.agent_id,
                "role": spec.role.value,
                "score": round(min(score, 1.0), 3),
                "activeAgents": len(active),
                "idleAgents": idle_count,
            })

        if not candidates:
            return {"swarmId": None, "agentId": None, "confidence": 0.0, "reason": "No swarms with matching capabilities"}

        candidates.sort(key=lambda c: c["score"], reverse=True)
        best = candidates[0]
        return {
            "swarmId": best["swarmId"],
            "agentId": best["agentId"],
            "role": best["role"],
            "confidence": best["score"],
            "reason": f"Routed to {best['role']} swarm with {best['idleAgents']} idle agents",
        }

    def assign_task(self, swarm_id: str, agent_id: str, task_id: str) -> bool:
        """Assign a task to a specific agent in a swarm."""
        if swarm_id not in self._agents:
            return False

        for agent in self._agents[swarm_id]:
            if agent.agent_id == agent_id:
                agent.state = SwarmState.ACTIVE
                agent.current_task_id = task_id
                agent.last_active_at = time.time()
                self._update_metrics(swarm_id)
                return True
        return False

    def complete_task(self, swarm_id: str, agent_id: str, success: bool, latency_ms: float, confidence: float = 0.0) -> None:
        """Mark a task as completed on an agent."""
        if swarm_id not in self._agents:
            return

        for agent in self._agents[swarm_id]:
            if agent.agent_id == agent_id:
                agent.current_task_id = None
                agent.last_active_at = time.time()
                if success:
                    agent.tasks_completed += 1
                else:
                    agent.tasks_failed += 1
                agent.total_latency_ms += latency_ms
                agent.confidence_score = (agent.confidence_score + confidence) / 2
                agent.state = SwarmState.IDLE
                self._update_metrics(swarm_id)
                break

    # ─── Auto-Scaling ─────────────────────────────────────────────────────────

    def auto_scale(self, swarm_id: str) -> dict[str, Any]:
        """
        Check utilization and scale a swarm up or down as needed.

        Returns scaling action taken.
        """
        if swarm_id not in self._swarms or swarm_id not in self._metrics:
            return {"action": "none", "reason": "Swarm not found"}

        spec = self._swarms[swarm_id]
        metrics = self._metrics[swarm_id]

        now = time.time()
        since_last_scale = now - metrics.last_scaled_at if metrics.last_scaled_at > 0 else float("inf")

        if since_last_scale < spec.cooldown_seconds:
            return {"action": "none", "reason": f"Cooldown active ({since_last_scale:.0f}s < {spec.cooldown_seconds}s)"}

        utilization = metrics.utilization_pct / 100.0
        action = "none"
        reason = ""

        if utilization >= spec.scale_up_threshold and metrics.agent_count < spec.max_agents:
            count = min(2, spec.max_agents - metrics.agent_count)
            new_agents = self.spawn_agents(swarm_id, count)
            if new_agents:
                action = "scaled_up"
                metrics.last_scaled_at = now
                reason = f"Utilization {utilization:.0%} ≥ threshold {spec.scale_up_threshold:.0%}, added {len(new_agents)} agents"

        elif utilization <= spec.scale_down_threshold and metrics.agent_count > spec.min_agents:
            count = min(1, metrics.agent_count - spec.min_agents)
            killed = self.kill_agents(swarm_id, count)
            if killed > 0:
                action = "scaled_down"
                metrics.last_scaled_at = now
                reason = f"Utilization {utilization:.0%} ≤ threshold {spec.scale_down_threshold:.0%}, removed {killed} agents"

        return {"action": action, "reason": reason, "utilizationPct": round(utilization * 100, 1)}

    # ─── Swarm Communication Protocol ─────────────────────────────────────────

    def send_message(self, message: SwarmProtocolMessage) -> bool:
        """Send a message between swarms."""
        if message.target_swarm_id not in self._swarms and message.message_type != "broadcast":
            return False

        message.timestamp = time.time()
        self._message_queue.append(message)

        if len(self._message_queue) > self._max_messages:
            self._message_queue = self._message_queue[-self._max_messages:]

        return True

    def get_messages(self, swarm_id: str, limit: int = 50) -> list[dict]:
        """Get messages addressed to or broadcast to a swarm."""
        result = []
        for msg in self._message_queue:
            if msg.target_swarm_id == swarm_id or msg.message_type == "broadcast":
                result.append(msg.to_dict())
        return result[-limit:]

    def merge_swarms(self, source_swarm_id: str, target_swarm_id: str) -> dict[str, Any]:
        """
        Merge two swarms. Agents from source are folded into target.
        """
        if source_swarm_id not in self._swarms or target_swarm_id not in self._swarms:
            return {"success": False, "reason": "One or both swarms not found"}

        source_spec = self._swarms.get(source_swarm_id)
        target_spec = self._swarms.get(target_swarm_id)

        source_agents = self._agents.get(source_swarm_id, [])
        target_agents = self._agents.get(target_swarm_id, [])

        available = target_spec.max_agents - len(target_agents)
        if available <= 0:
            return {"success": False, "reason": f"Target swarm at capacity ({len(target_agents)}/{target_spec.max_agents})"}

        # Move agents up to available slots
        moved = 0
        for agent in source_agents[:available]:
            agent.swarm_role = target_spec.role
            target_agents.append(agent)
            moved += 1

        self._agents[source_swarm_id] = source_agents[available:]
        self._agents[target_swarm_id] = target_agents

        # If source is now empty, terminate it
        if not self._agents[source_swarm_id]:
            self.terminate_swarm(source_swarm_id)

        self._update_metrics(target_swarm_id)

        return {"success": True, "movedAgents": moved, "targetAgentCount": len(target_agents)}

    # ─── Health Monitoring ────────────────────────────────────────────────────

    def health_check(self, swarm_id: str) -> SwarmHealthReport:
        """Perform a health check on a swarm."""
        if swarm_id not in self._swarms:
            return SwarmHealthReport(
                swarm_id=swarm_id, role="unknown", state="not_found", is_healthy=False,
                issues=["Swarm not found"],
            )

        spec = self._swarms[swarm_id]
        agents = self._agents.get(swarm_id, [])
        metrics = self._metrics.get(swarm_id)

        active = sum(1 for a in agents if a.state in (SwarmState.ACTIVE, SwarmState.IDLE))
        failed = sum(1 for a in agents if a.state == SwarmState.FAILED)
        total_tasks = sum(a.tasks_completed + a.tasks_failed for a in agents)
        failed_tasks = sum(a.tasks_failed for a in agents)
        error_rate = failed_tasks / total_tasks if total_tasks > 0 else 0.0
        avg_latency = sum(a.avg_latency_ms for a in agents) / len(agents) if agents else 0.0

        issues: list[str] = []
        if failed > 0:
            issues.append(f"{failed} agent(s) in FAILED state")
        if error_rate > 0.1:
            issues.append(f"Error rate {error_rate:.1%} exceeds 10% threshold")
        if active == 0:
            issues.append("No active agents available")
        if metrics and metrics.utilization_pct > 90:
            issues.append(f"Utilization at {metrics.utilization_pct:.0f}% — nearing capacity")

        return SwarmHealthReport(
            swarm_id=swarm_id,
            role=spec.role.value,
            state=schedule_state(spec.role),
            is_healthy=len(issues) == 0,
            agent_count=len(agents),
            active_agents=active,
            failed_agents=failed,
            utilization=metrics.utilization_pct if metrics else 0.0,
            error_rate=error_rate,
            avg_latency_ms=avg_latency,
            issues=issues,
            last_check=time.time(),
        )

    def health_check_all(self) -> list[dict]:
        """Health check all swarms."""
        return [self.health_check(sid).to_dict() for sid in self._swarms]

    def heal_swarm(self, swarm_id: str) -> dict[str, Any]:
        """Attempt to heal a degraded swarm by replacing failed agents."""
        report = self.health_check(swarm_id)
        if report.is_healthy:
            return {"action": "none", "reason": "Swarm is healthy"}

        spec = self._swarms.get(swarm_id)
        if not spec:
            return {"action": "none", "reason": "Swarm not found"}

        agents = self._agents.get(swarm_id, [])
        failed = [a for a in agents if a.state == SwarmState.FAILED]

        # Replace failed agents
        replaced = 0
        for agent in failed:
            agent.state = SwarmState.SPAWNING

        # Spawn replacements if we dropped below min
        current_active = len([a for a in agents if a.state in (SwarmState.ACTIVE, SwarmState.IDLE, SwarmState.SPAWNING)])
        deficit = spec.min_agents - current_active
        if deficit > 0:
            new_agents = self.spawn_agents(swarm_id, deficit)
            replaced += len(new_agents)

        replaced += len(failed)
        self._update_metrics(swarm_id)

        return {"action": "healed", "agentsReplaced": replaced, "reason": f"Replaced {replaced} failed agent(s)"}

    # ─── Metrics & Reporting ─────────────────────────────────────────────────

    def _update_metrics(self, swarm_id: str) -> None:
        """Recalculate metrics for a swarm."""
        if swarm_id not in self._swarms or swarm_id not in self._agents:
            return

        spec = self._swarms[swarm_id]
        agents = self._agents[swarm_id]
        metrics = self._metrics.get(swarm_id)

        if not agents or not metrics:
            return

        active = sum(1 for a in agents if a.state in (SwarmState.ACTIVE, SwarmState.IDLE))
        idle = sum(1 for a in agents if a.state == SwarmState.IDLE)
        running = sum(1 for a in agents if a.state == SwarmState.ACTIVE)
        total_completed = sum(a.tasks_completed for a in agents)
        total_failed = sum(a.tasks_failed for a in agents)
        total_tasks = total_completed + total_failed
        success_rate = total_completed / total_tasks if total_tasks > 0 else 1.0
        avg_latency = sum(a.avg_latency_ms for a in agents) / len(agents) if agents else 0.0
        avg_confidence = sum(a.confidence_score for a in agents) / len(agents) if agents else 0.0
        utilization = (running / max(spec.max_concurrent_tasks, 1)) * 100

        metrics.agent_count = len(agents)
        metrics.active_agents = active
        metrics.idle_agents = idle
        metrics.total_tasks_completed = total_completed
        metrics.total_tasks_failed = total_failed
        metrics.total_tasks_running = running
        metrics.avg_success_rate = success_rate
        metrics.avg_latency_ms = avg_latency
        metrics.avg_confidence = avg_confidence
        metrics.utilization_pct = min(utilization, 100.0)
        metrics.uptime_seconds = time.time() - min(a.spawned_at for a in agents) if agents else 0.0

    def get_swarm(self, swarm_id: str) -> dict[str, Any] | None:
        """Get full swarm details."""
        spec = self._swarms.get(swarm_id)
        if not spec:
            return None

        agents = self._agents.get(swarm_id, [])
        metrics = self._metrics.get(swarm_id)

        return {
            "swarmId": swarm_id,
            "role": spec.role.value,
            "state": schedule_state(spec.role),
            "spec": {
                "minAgents": spec.min_agents,
                "maxAgents": spec.max_agents,
                "initialAgents": spec.initial_agents,
                "capabilities": [c.value for c in spec.capabilities],
                "priority": spec.priority,
                "autoScale": spec.auto_scale,
                "maxConcurrentTasks": spec.max_concurrent_tasks,
                "retryOnFailure": spec.retry_on_failure,
            },
            "agents": [a.to_dict() for a in agents],
            "metrics": metrics.to_dict() if metrics else None,
        }

    def list_swarms(self) -> list[dict[str, Any]]:
        """List all swarms with summary info."""
        return [
            {
                "swarmId": sid,
                "role": spec.role.value,
                "agentCount": len(self._agents.get(sid, [])),
                "state": schedule_state(spec.role),
            }
            for sid, spec in self._swarms.items()
        ]

    def get_status(self) -> dict[str, Any]:
        """Get overall swarm system status."""
        total_swarms = len(self._swarms)
        total_agents = sum(len(a) for a in self._agents.values())
        active_agents = sum(
            sum(1 for a in agents if a.state in (SwarmState.ACTIVE, SwarmState.IDLE))
            for agents in self._agents.values()
        )

        return {
            "totalSwarms": total_swarms,
            "totalAgents": total_agents,
            "activeAgents": active_agents,
            "messageQueueSize": len(self._message_queue),
            "swarmRoles": [spec.role.value for spec in self._swarms.values()],
        }

    def reset(self) -> None:
        """Reset the swarm manager (for testing)."""
        self._swarms.clear()
        self._agents.clear()
        self._metrics.clear()
        self._message_queue.clear()


def schedule_state(role: SwarmRole) -> str:
    return "active"
