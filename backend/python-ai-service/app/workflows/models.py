"""
Workflow data models — defines the graph structure, node types, and execution state.

Each workflow is a directed acyclic graph (DAG) of typed nodes connected by edges.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Literal
from datetime import datetime


class WorkflowStatus(str, Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    RUNNING = "running"
    PAUSED = "paused"
    ERROR = "error"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class NodeType(str, Enum):
    TRIGGER = "trigger"
    LLM = "llm"
    TOOL = "tool"
    CONDITION = "condition"
    AGENT = "agent"
    DELAY = "delay"
    OUTPUT = "output"
    CODE = "code"
    MEMORY = "memory"
    SEARCH = "search"
    VISION = "vision"
    VOICE = "voice"
    WEBHOOK = "webhook"
    SCHEDULER = "scheduler"


class TriggerType(str, Enum):
    MANUAL = "manual"
    SCHEDULED = "scheduled"
    WEBHOOK = "webhook"
    EVENT = "event"
    CHAT = "chat"


class WorkflowNode:
    """A single node in a workflow graph."""

    def __init__(
        self,
        id: str,
        type: NodeType | str,
        label: str,
        config: dict[str, Any] | None = None,
        position: tuple[float, float] = (0, 0),
    ):
        self.id = id
        self.type = NodeType(type) if isinstance(type, str) else type
        self.label = label
        self.config = config or {}
        self.position = position

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "type": self.type.value,
            "label": self.label,
            "config": self.config,
            "position": {"x": self.position[0], "y": self.position[1]},
        }

    @classmethod
    def from_dict(cls, data: dict) -> "WorkflowNode":
        pos = data.get("position", {})
        return cls(
            id=data["id"],
            type=data["type"],
            label=data.get("label", ""),
            config=data.get("config", {}),
            position=(pos.get("x", 0), pos.get("y", 0)),
        )


class WorkflowEdge:
    """A directed edge connecting two nodes."""

    def __init__(
        self,
        id: str,
        source: str,
        target: str,
        label: str = "",
        condition: str | None = None,
    ):
        self.id = id
        self.source = source
        self.target = target
        self.label = label
        self.condition = condition  # Optional condition expression

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "source": self.source,
            "target": self.target,
            "label": self.label,
            "condition": self.condition,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "WorkflowEdge":
        return cls(
            id=data["id"],
            source=data["source"],
            target=data["target"],
            label=data.get("label", ""),
            condition=data.get("condition"),
        )


class WorkflowDefinition:
    """Complete workflow definition — a DAG of nodes + edges."""

    def __init__(
        self,
        id: str,
        name: str,
        description: str = "",
        nodes: list[WorkflowNode] | None = None,
        edges: list[WorkflowEdge] | None = None,
        status: WorkflowStatus = WorkflowStatus.DRAFT,
        tags: list[str] | None = None,
        created_at: str | None = None,
        updated_at: str | None = None,
    ):
        self.id = id
        self.name = name
        self.description = description
        self.nodes = nodes or []
        self.edges = edges or []
        self.status = status
        self.tags = tags or []
        self.created_at = created_at or datetime.utcnow().isoformat()
        self.updated_at = updated_at or datetime.utcnow().isoformat()

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "nodes": [n.to_dict() for n in self.nodes],
            "edges": [e.to_dict() for e in self.edges],
            "status": self.status.value,
            "tags": self.tags,
            "createdAt": self.created_at,
            "updatedAt": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "WorkflowDefinition":
        return cls(
            id=data["id"],
            name=data.get("name", ""),
            description=data.get("description", ""),
            nodes=[WorkflowNode.from_dict(n) for n in data.get("nodes", [])],
            edges=[WorkflowEdge.from_dict(e) for e in data.get("edges", [])],
            status=WorkflowStatus(data.get("status", "draft")),
            tags=data.get("tags", []),
            created_at=data.get("createdAt"),
            updated_at=data.get("updatedAt"),
        )

    def validate(self) -> list[str]:
        """Validate the workflow graph. Returns list of errors (empty = valid)."""
        errors: list[str] = []
        node_ids = {n.id for n in self.nodes}

        # Check all edge references are valid
        for edge in self.edges:
            if edge.source not in node_ids:
                errors.append(f"Edge {edge.id}: source '{edge.source}' not found")
            if edge.target not in node_ids:
                errors.append(f"Edge {edge.id}: target '{edge.target}' not found")

        # Check at least one trigger node
        triggers = [n for n in self.nodes if n.type == NodeType.TRIGGER]
        if not triggers:
            errors.append("Workflow must have at least one trigger node")

        # Check no cycles (simple BFS)
        visited: set[str] = set()
        recursion_stack: set[str] = set()

        def detect_cycle(node_id: str) -> bool:
            visited.add(node_id)
            recursion_stack.add(node_id)
            for edge in self.edges:
                if edge.source == node_id:
                    if edge.target not in visited:
                        if detect_cycle(edge.target):
                            return True
                    elif edge.target in recursion_stack:
                        return True
            recursion_stack.discard(node_id)
            return False

        for nid in node_ids:
            if nid not in visited:
                if detect_cycle(nid):
                    errors.append(f"Cycle detected starting at node '{nid}'")
                    break

        return errors


class WorkflowExecution:
    """Runtime state of a single workflow execution."""

    def __init__(
        self,
        id: str,
        workflow_id: str,
        status: WorkflowStatus = WorkflowStatus.RUNNING,
        current_node_id: str | None = None,
        context: dict[str, Any] | None = None,
        started_at: str | None = None,
        completed_at: str | None = None,
        error: str | None = None,
    ):
        self.id = id
        self.workflow_id = workflow_id
        self.status = status
        self.current_node_id = current_node_id
        self.context = context or {}
        self.started_at = started_at or datetime.utcnow().isoformat()
        self.completed_at = completed_at
        self.error = error

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "workflowId": self.workflow_id,
            "status": self.status.value,
            "currentNodeId": self.current_node_id,
            "context": self.context,
            "startedAt": self.started_at,
            "completedAt": self.completed_at,
            "error": self.error,
        }
