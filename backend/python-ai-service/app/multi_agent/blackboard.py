"""
SharedBlackboard — shared state/memory for all agents in a session.

Agents read/write named slots. Changes are versioned and broadcast to
the AgentBus so all agents can react to state changes.

Slot types:
  - Any JSON-serialisable value
  - Tags for filtering (e.g. "result", "plan", "draft")
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class BlackboardEntry:
    key: str
    value: Any
    author_id: str
    author_name: str
    version: int = 1
    timestamp: float = field(default_factory=time.time)
    tags: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "value": self.value,
            "author_id": self.author_id,
            "author_name": self.author_name,
            "version": self.version,
            "timestamp": self.timestamp,
            "tags": self.tags,
        }


class SharedBlackboard:
    """
    Thread-safe (asyncio) shared blackboard for multi-agent sessions.

    One Blackboard per session_id. Use BlackboardRegistry to get/create.
    """

    def __init__(self, session_id: str):
        self.session_id = session_id
        self._slots: dict[str, BlackboardEntry] = {}
        self._changelog: list[dict] = []

    def write(
        self,
        key: str,
        value: Any,
        author_id: str,
        author_name: str = "",
        tags: list[str] | None = None,
        broadcast: bool = True,
    ) -> BlackboardEntry:
        """Write a value to a slot. If slot exists, increments version."""
        existing = self._slots.get(key)
        version = (existing.version + 1) if existing else 1
        entry = BlackboardEntry(
            key=key,
            value=value,
            author_id=author_id,
            author_name=author_name,
            version=version,
            tags=tags or [],
        )
        self._slots[key] = entry
        change = {
            "action": "write",
            "key": key,
            "author_id": author_id,
            "version": version,
            "timestamp": entry.timestamp,
        }
        self._changelog.append(change)
        logger.debug("blackboard_write", session=self.session_id, key=key, author=author_id, version=version)

        # optionally broadcast to AgentBus
        if broadcast:
            try:
                import asyncio
                from app.multi_agent.agent_bus import AgentBus, AgentMessage
                bus = AgentBus.get()
                msg = AgentMessage(
                    sender_id=author_id,
                    sender_name=author_name,
                    topic="blackboard",
                    content=f"[blackboard] {author_name} wrote '{key}' (v{version})",
                    payload={"key": key, "value": value, "version": version, "tags": tags or []},
                    msg_type="status",
                )
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    asyncio.ensure_future(bus.publish(msg))
            except Exception:
                pass  # blackboard write must never fail due to bus errors

        return entry

    def read(self, key: str) -> Any:
        entry = self._slots.get(key)
        return entry.value if entry else None

    def read_entry(self, key: str) -> BlackboardEntry | None:
        return self._slots.get(key)

    def read_by_tag(self, tag: str) -> list[BlackboardEntry]:
        return [e for e in self._slots.values() if tag in e.tags]

    def keys(self) -> list[str]:
        return list(self._slots.keys())

    def snapshot(self) -> dict[str, Any]:
        return {k: e.to_dict() for k, e in self._slots.items()}

    def changelog(self, limit: int = 50) -> list[dict]:
        return self._changelog[-limit:]

    def to_context_str(self, max_entries: int = 20) -> str:
        """Render blackboard as a compact context string for LLM prompts."""
        lines = [f"=== Shared Blackboard (session: {self.session_id}) ==="]
        for key, entry in list(self._slots.items())[:max_entries]:
            val_str = str(entry.value)[:200]
            lines.append(f"[{key}] by {entry.author_name}: {val_str}")
        return "\n".join(lines)


class BlackboardRegistry:
    """Global registry of per-session blackboards."""

    _instance: BlackboardRegistry | None = None
    _boards: dict[str, SharedBlackboard] = {}

    @classmethod
    def get(cls) -> BlackboardRegistry:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def get_or_create(self, session_id: str) -> SharedBlackboard:
        if session_id not in self._boards:
            self._boards[session_id] = SharedBlackboard(session_id)
        return self._boards[session_id]

    def get_board(self, session_id: str) -> SharedBlackboard | None:
        return self._boards.get(session_id)

    def list_sessions(self) -> list[str]:
        return list(self._boards.keys())

    def drop(self, session_id: str) -> None:
        self._boards.pop(session_id, None)
