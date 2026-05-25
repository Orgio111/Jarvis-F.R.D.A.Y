"""
Swarm Manager — data models for distributed autonomous agent swarms.

Defines the core types used across the swarm system:
  - SwarmSpec: configuration for spawning a swarm
  - SwarmAgent: a single agent within a swarm
  - SwarmMetrics: performance tracking for a swarm
  - SwarmProtocolMessage: inter-swarm communication envelope
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any
from uuid import uuid4


class SwarmRole(Enum):
    """Pre-defined swarm roles in the JARVIS architecture."""

    RESEARCH = "research"
    CODING = "coding"
    PLANNER = "planner"
    SECURITY = "security"
    BROWSER = "browser"
    DEVOPS = "devops"
    VISION = "vision"
    VOICE = "voice"
    GENERAL = "general"


class AgentCapability(Enum):
    """Capabilities an individual agent can possess."""

    WEB_SEARCH = "web_search"
    CODE_GENERATION = "code_generation"
    CODE_REVIEW = "code_review"
    FILE_OPS = "file_ops"
    BROWSER_NAV = "browser_navigation"
    BROWSER_SCRAPE = "browser_scrape"
    API_CALL = "api_call"
    TOOL_EXECUTION = "tool_execution"
    MEMORY_READ = "memory_read"
    MEMORY_WRITE = "memory_write"
    REASONING = "reasoning"
    PLANNING = "planning"
    VALIDATION = "validation"
    DEVOPS_DEPLOY = "devops_deploy"
    DEVOPS_MONITOR = "devops_monitor"
    VISION_OCR = "vision_ocr"
    VISION_ANALYSIS = "vision_analysis"
    VOICE_STT = "voice_stt"
    VOICE_TTS = "voice_tts"
    SECURITY_SCAN = "security_scan"
    SECURITY_AUDIT = "security_audit"
    WORKFLOW_EXEC = "workflow_execution"
    WORKFLOW_DESIGN = "workflow_design"


class SwarmState(Enum):
    """Lifecycle state of a swarm."""

    PENDING = "pending"
    SPAWNING = "spawning"
    ACTIVE = "active"
    IDLE = "idle"
    SCALING = "scaling"
    MERGING = "merging"
    DEGRADED = "degraded"
    TERMINATING = "terminating"
    TERMINATED = "terminated"
    FAILED = "failed"


@dataclass
class SwarmSpec:
    """Specification for spawning a new swarm."""

    role: SwarmRole
    min_agents: int = 1
    max_agents: int = 5
    initial_agents: int = 1
    capabilities: list[AgentCapability] = field(default_factory=list)
    priority: int = 5  # 1 (lowest) – 10 (highest)
    auto_scale: bool = True
    scale_up_threshold: float = 0.8  # avg utilization % to trigger scale-up
    scale_down_threshold: float = 0.2  # avg utilization % to trigger scale-down
    cooldown_seconds: int = 60
    labels: dict[str, str] = field(default_factory=dict)
    max_concurrent_tasks: int = 10
    execution_timeout_s: int = 300
    retry_on_failure: bool = True
    max_retries: int = 2

    @classmethod
    def default_for_role(cls, role: SwarmRole) -> SwarmSpec:
        specs = {
            SwarmRole.RESEARCH: SwarmSpec(
                role=role, min_agents=1, max_agents=4,
                capabilities=[AgentCapability.WEB_SEARCH, AgentCapability.MEMORY_READ, AgentCapability.MEMORY_WRITE, AgentCapability.REASONING],
                priority=6,
            ),
            SwarmRole.CODING: SwarmSpec(
                role=role, min_agents=1, max_agents=5,
                capabilities=[AgentCapability.CODE_GENERATION, AgentCapability.CODE_REVIEW, AgentCapability.FILE_OPS, AgentCapability.API_CALL],
                priority=8,
            ),
            SwarmRole.PLANNER: SwarmSpec(
                role=role, min_agents=1, max_agents=3,
                capabilities=[AgentCapability.PLANNING, AgentCapability.REASONING, AgentCapability.WORKFLOW_DESIGN],
                priority=9,
            ),
            SwarmRole.SECURITY: SwarmSpec(
                role=role, min_agents=1, max_agents=3,
                capabilities=[AgentCapability.SECURITY_SCAN, AgentCapability.SECURITY_AUDIT, AgentCapability.VALIDATION],
                priority=7,
            ),
            SwarmRole.BROWSER: SwarmSpec(
                role=role, min_agents=1, max_agents=3,
                capabilities=[AgentCapability.BROWSER_NAV, AgentCapability.BROWSER_SCRAPE, AgentCapability.VISION_OCR],
                priority=5,
            ),
            SwarmRole.DEVOPS: SwarmSpec(
                role=role, min_agents=1, max_agents=3,
                capabilities=[AgentCapability.DEVOPS_DEPLOY, AgentCapability.DEVOPS_MONITOR, AgentCapability.TOOL_EXECUTION],
                priority=7,
            ),
            SwarmRole.VISION: SwarmSpec(
                role=role, min_agents=1, max_agents=3,
                capabilities=[AgentCapability.VISION_ANALYSIS, AgentCapability.VISION_OCR],
                priority=5,
            ),
            SwarmRole.VOICE: SwarmSpec(
                role=role, min_agents=1, max_agents=2,
                capabilities=[AgentCapability.VOICE_STT, AgentCapability.VOICE_TTS],
                priority=4,
            ),
            SwarmRole.GENERAL: SwarmSpec(
                role=role, min_agents=1, max_agents=3,
                capabilities=[AgentCapability.REASONING, AgentCapability.TOOL_EXECUTION, AgentCapability.API_CALL],
                priority=5,
            ),
        }
        return specs.get(role, SwarmSpec(role=role))


@dataclass
class SwarmAgent:
    """A single agent within a swarm."""

    agent_id: str = field(default_factory=lambda: f"agent_{uuid4().hex[:8]}")
    swarm_role: SwarmRole = SwarmRole.GENERAL
    capabilities: list[AgentCapability] = field(default_factory=list)
    state: SwarmState = SwarmState.PENDING
    spawned_at: float = 0.0
    last_active_at: float = 0.0
    tasks_completed: int = 0
    tasks_failed: int = 0
    total_latency_ms: float = 0.0
    confidence_score: float = 0.0
    current_task_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def success_rate(self) -> float:
        total = self.tasks_completed + self.tasks_failed
        if total == 0:
            return 1.0
        return self.tasks_completed / total

    @property
    def avg_latency_ms(self) -> float:
        if self.tasks_completed == 0:
            return 0.0
        return self.total_latency_ms / self.tasks_completed

    def to_dict(self) -> dict[str, Any]:
        return {
            "agentId": self.agent_id,
            "swarmRole": self.swarm_role.value,
            "capabilities": [c.value for c in self.capabilities],
            "state": self.state.value,
            "spawnedAt": self.spawned_at,
            "lastActiveAt": self.last_active_at,
            "tasksCompleted": self.tasks_completed,
            "tasksFailed": self.tasks_failed,
            "successRate": round(self.success_rate, 3),
            "avgLatencyMs": round(self.avg_latency_ms, 1),
            "confidenceScore": round(self.confidence_score, 2),
            "currentTaskId": self.current_task_id,
        }


@dataclass
class SwarmMetrics:
    """Aggregate performance metrics for a swarm."""

    swarm_id: str
    role: str
    agent_count: int = 0
    active_agents: int = 0
    idle_agents: int = 0
    total_tasks_completed: int = 0
    total_tasks_failed: int = 0
    total_tasks_running: int = 0
    avg_success_rate: float = 1.0
    avg_latency_ms: float = 0.0
    avg_confidence: float = 0.0
    utilization_pct: float = 0.0
    uptime_seconds: float = 0.0
    last_scaled_at: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "swarmId": self.swarm_id,
            "role": self.role,
            "agentCount": self.agent_count,
            "activeAgents": self.active_agents,
            "idleAgents": self.idle_agents,
            "totalTasksCompleted": self.total_tasks_completed,
            "totalTasksFailed": self.total_tasks_failed,
            "totalTasksRunning": self.total_tasks_running,
            "avgSuccessRate": round(self.avg_success_rate, 3),
            "avgLatencyMs": round(self.avg_latency_ms, 1),
            "avgConfidence": round(self.avg_confidence, 2),
            "utilizationPct": round(self.utilization_pct, 1),
            "uptimeSeconds": round(self.uptime_seconds, 1),
            "lastScaledAt": self.last_scaled_at,
        }


@dataclass
class SwarmProtocolMessage:
    """Inter-swarm communication message envelope."""

    message_id: str = field(default_factory=lambda: f"msg_{uuid4().hex[:8]}")
    source_swarm_id: str = ""
    target_swarm_id: str = ""
    message_type: str = "request"  # request, response, broadcast, event
    action: str = ""
    payload: dict[str, Any] = field(default_factory=dict)
    priority: int = 5
    timestamp: float = 0.0
    ttl_seconds: int = 60
    correlation_id: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "messageId": self.message_id,
            "sourceSwarmId": self.source_swarm_id,
            "targetSwarmId": self.target_swarm_id,
            "messageType": self.message_type,
            "action": self.action,
            "payload": self.payload,
            "priority": self.priority,
            "timestamp": self.timestamp,
            "ttlSeconds": self.ttl_seconds,
            "correlationId": self.correlation_id,
        }


@dataclass
class SwarmHealthReport:
    """Health report for a swarm."""

    swarm_id: str
    role: str
    state: str
    is_healthy: bool = True
    agent_count: int = 0
    active_agents: int = 0
    failed_agents: int = 0
    utilization: float = 0.0
    error_rate: float = 0.0
    avg_latency_ms: float = 0.0
    issues: list[str] = field(default_factory=list)
    last_check: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "swarmId": self.swarm_id,
            "role": self.role,
            "state": self.state,
            "isHealthy": self.is_healthy,
            "agentCount": self.agent_count,
            "activeAgents": self.active_agents,
            "failedAgents": self.failed_agents,
            "utilization": round(self.utilization, 1),
            "errorRate": round(self.error_rate, 3),
            "avgLatencyMs": round(self.avg_latency_ms, 1),
            "issues": self.issues,
            "lastCheck": self.last_check,
        }
