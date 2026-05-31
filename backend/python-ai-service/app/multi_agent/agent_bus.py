"""
AgentBus — central message bus for agent-to-agent (A2A) communication.

Features:
  - pub/sub topic-based messaging
  - direct agent-to-agent messaging
  - message history (ring buffer per topic)
  - async delivery to registered subscribers
  - SSE-compatible event stream
"""
from __future__ import annotations

import asyncio
import time
import uuid
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Callable, Awaitable

from app.core.logging import get_logger

logger = get_logger(__name__)

MessageHandler = Callable[["AgentMessage"], Awaitable[None]]


@dataclass
class AgentMessage:
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    sender_id: str = ""
    sender_name: str = ""
    recipient_id: str | None = None   # None = broadcast to topic
    topic: str = "general"
    content: str = ""
    payload: dict[str, Any] = field(default_factory=dict)
    msg_type: str = "message"         # message | task | result | error | status
    timestamp: float = field(default_factory=time.time)
    parent_msg_id: str | None = None  # for reply chains

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "sender_id": self.sender_id,
            "sender_name": self.sender_name,
            "recipient_id": self.recipient_id,
            "topic": self.topic,
            "content": self.content,
            "payload": self.payload,
            "msg_type": self.msg_type,
            "timestamp": self.timestamp,
            "parent_msg_id": self.parent_msg_id,
        }


class AgentBus:
    """
    Central async message bus.

    Agents register with subscribe(topic, handler).
    Messages are delivered to:
      1. Direct recipient (if recipient_id set)
      2. All topic subscribers
      3. Wildcard "*" subscribers (monitor/logger agents)
    """

    _instance: AgentBus | None = None

    def __init__(self, history_size: int = 500):
        self._subscribers: dict[str, list[tuple[str, MessageHandler]]] = {}
        # agent_id → handler for direct messages
        self._direct: dict[str, MessageHandler] = {}
        # topic → ring buffer of recent messages
        self._history: dict[str, deque[AgentMessage]] = {}
        self._history_size = history_size
        # global SSE listeners (asyncio queues)
        self._sse_queues: list[asyncio.Queue] = []
        self._lock = asyncio.Lock()

    @classmethod
    def get(cls) -> AgentBus:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    # ── Registration ──────────────────────────────────────────────────────────

    def subscribe(self, topic: str, agent_id: str, handler: MessageHandler) -> None:
        """Subscribe an agent to a topic."""
        if topic not in self._subscribers:
            self._subscribers[topic] = []
        # prevent duplicate
        self._subscribers[topic] = [
            (aid, h) for aid, h in self._subscribers[topic] if aid != agent_id
        ]
        self._subscribers[topic].append((agent_id, handler))
        logger.debug("agent_bus_subscribe", agent_id=agent_id, topic=topic)

    def unsubscribe(self, topic: str, agent_id: str) -> None:
        if topic in self._subscribers:
            self._subscribers[topic] = [
                (aid, h) for aid, h in self._subscribers[topic] if aid != agent_id
            ]

    def register_direct(self, agent_id: str, handler: MessageHandler) -> None:
        """Register handler for direct (unicast) messages to this agent."""
        self._direct[agent_id] = handler

    def unregister_direct(self, agent_id: str) -> None:
        self._direct.pop(agent_id, None)

    def add_sse_queue(self, q: asyncio.Queue) -> None:
        self._sse_queues.append(q)

    def remove_sse_queue(self, q: asyncio.Queue) -> None:
        if q in self._sse_queues:
            self._sse_queues.remove(q)

    # ── Publishing ────────────────────────────────────────────────────────────

    async def publish(self, msg: AgentMessage) -> None:
        """
        Publish a message.
        Delivery order: direct recipient → topic subscribers → wildcard monitors.
        """
        # store in history
        if msg.topic not in self._history:
            self._history[msg.topic] = deque(maxlen=self._history_size)
        self._history[msg.topic].append(msg)

        logger.info(
            "agent_bus_message",
            sender=msg.sender_id,
            recipient=msg.recipient_id or f"[{msg.topic}]",
            type=msg.msg_type,
            preview=msg.content[:60],
        )

        # push to SSE
        for q in list(self._sse_queues):
            try:
                q.put_nowait(msg.to_dict())
            except asyncio.QueueFull:
                pass

        # direct delivery
        if msg.recipient_id and msg.recipient_id in self._direct:
            await self._safe_call(self._direct[msg.recipient_id], msg)
            return  # direct = unicast, don't broadcast

        # topic broadcast
        for agent_id, handler in list(self._subscribers.get(msg.topic, [])):
            if agent_id != msg.sender_id:  # don't echo back to sender
                await self._safe_call(handler, msg)

        # wildcard monitors (always receive, even direct messages)
        for agent_id, handler in list(self._subscribers.get("*", [])):
            if agent_id != msg.sender_id:
                await self._safe_call(handler, msg)

    async def _safe_call(self, handler: MessageHandler, msg: AgentMessage) -> None:
        try:
            await handler(msg)
        except Exception as exc:
            logger.warning("agent_bus_handler_error", error=str(exc))

    # ── History ───────────────────────────────────────────────────────────────

    def get_history(self, topic: str, limit: int = 50) -> list[dict]:
        buf = self._history.get(topic, deque())
        msgs = list(buf)[-limit:]
        return [m.to_dict() for m in msgs]

    def get_all_history(self, limit: int = 100) -> list[dict]:
        all_msgs: list[AgentMessage] = []
        for buf in self._history.values():
            all_msgs.extend(buf)
        all_msgs.sort(key=lambda m: m.timestamp)
        return [m.to_dict() for m in all_msgs[-limit:]]

    def get_status(self) -> dict[str, Any]:
        return {
            "topics": list(self._subscribers.keys()),
            "direct_agents": list(self._direct.keys()),
            "sse_listeners": len(self._sse_queues),
            "history_topics": {t: len(b) for t, b in self._history.items()},
        }
