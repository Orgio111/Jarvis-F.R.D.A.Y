"""Session Replay data models."""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any
from uuid import uuid4


class EventKind(str, Enum):
    USER_MESSAGE   = "user_message"
    AGENT_MESSAGE  = "agent_message"
    TOOL_CALL      = "tool_call"
    TOOL_RESULT    = "tool_result"
    WORKFLOW_STEP  = "workflow_step"
    MODEL_SWITCH   = "model_switch"
    APPROVAL_REQ   = "approval_request"
    APPROVAL_RESP  = "approval_response"
    ERROR          = "error"
    METADATA       = "metadata"


@dataclass
class ReplayEvent:
    """A single captured event inside a session."""
    event_id:   str      = field(default_factory=lambda: f"evt_{uuid4().hex[:10]}")
    kind:       EventKind = EventKind.USER_MESSAGE
    timestamp:  float    = field(default_factory=time.time)
    data:       dict[str, Any] = field(default_factory=dict)
    model_used: str | None = None
    duration_ms: float = 0.0

    def to_dict(self) -> dict:
        return {
            "event_id":    self.event_id,
            "kind":        self.kind.value,
            "timestamp":   self.timestamp,
            "data":        self.data,
            "model_used":  self.model_used,
            "duration_ms": self.duration_ms,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "ReplayEvent":
        return cls(
            event_id=d.get("event_id", f"evt_{uuid4().hex[:10]}"),
            kind=EventKind(d.get("kind", "metadata")),
            timestamp=d.get("timestamp", time.time()),
            data=d.get("data", {}),
            model_used=d.get("model_used"),
            duration_ms=d.get("duration_ms", 0.0),
        )


@dataclass
class ReplaySession:
    """A complete recorded session (chat or workflow)."""
    session_id:  str      = field(default_factory=lambda: f"sess_{uuid4().hex[:12]}")
    title:       str      = "Untitled Session"
    session_type: str     = "chat"          # "chat" | "workflow" | "agent_run"
    started_at:  float    = field(default_factory=time.time)
    ended_at:    float | None = None
    events:      list[ReplayEvent] = field(default_factory=list)
    tags:        list[str] = field(default_factory=list)
    model_summary: dict[str, int] = field(default_factory=dict)  # model -> call count
    metadata:    dict[str, Any] = field(default_factory=dict)

    @property
    def duration_s(self) -> float:
        end = self.ended_at or time.time()
        return round(end - self.started_at, 2)

    @property
    def event_count(self) -> int:
        return len(self.events)

    def add_event(self, event: ReplayEvent) -> None:
        self.events.append(event)
        if event.model_used:
            self.model_summary[event.model_used] = \
                self.model_summary.get(event.model_used, 0) + 1

    def close(self) -> None:
        self.ended_at = time.time()

    def to_dict(self, include_events: bool = True) -> dict:
        d: dict[str, Any] = {
            "session_id":    self.session_id,
            "title":         self.title,
            "session_type":  self.session_type,
            "started_at":    self.started_at,
            "ended_at":      self.ended_at,
            "duration_s":    self.duration_s,
            "event_count":   self.event_count,
            "tags":          self.tags,
            "model_summary": self.model_summary,
            "metadata":      self.metadata,
        }
        if include_events:
            d["events"] = [e.to_dict() for e in self.events]
        return d

    @classmethod
    def from_dict(cls, d: dict) -> "ReplaySession":
        sess = cls(
            session_id=d["session_id"],
            title=d.get("title", "Untitled"),
            session_type=d.get("session_type", "chat"),
            started_at=d.get("started_at", time.time()),
            ended_at=d.get("ended_at"),
            tags=d.get("tags", []),
            model_summary=d.get("model_summary", {}),
            metadata=d.get("metadata", {}),
        )
        for e in d.get("events", []):
            sess.events.append(ReplayEvent.from_dict(e))
        return sess
