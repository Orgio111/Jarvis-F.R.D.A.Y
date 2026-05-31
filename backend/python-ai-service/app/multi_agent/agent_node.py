"""
AgentNode — base class for any agent that participates in the multi-agent bus.

Every concrete agent:
  1. Has a unique agent_id + human-readable name + role
  2. Registers itself on the AgentBus (topic + direct)
  3. Can send messages to any topic or agent
  4. Implements handle_message() to react to incoming messages
  5. Has a process_task() for direct task execution

Built-in node types (subclass to extend):
  - LLMAgentNode: uses provider LLM to respond
  - EchoAgentNode: for testing
"""
from __future__ import annotations

import asyncio
import time
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from app.core.logging import get_logger
from app.multi_agent.agent_bus import AgentBus, AgentMessage
from app.multi_agent.blackboard import BlackboardRegistry

logger = get_logger(__name__)


@dataclass
class AgentNodeSpec:
    """Spec used by AgentFactory to create a new AgentNode dynamically."""
    name: str
    role: str                      # coder | researcher | devops | analyst | writer | orchestrator | custom
    goal: str
    backstory: str = ""
    tools: list[str] = field(default_factory=list)
    topics: list[str] = field(default_factory=list)   # topics to subscribe to
    model_preference: str = ""
    max_tokens: int = 1024
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_system_prompt(self) -> str:
        return (
            f"You are {self.name}, a specialist AI agent.\n\n"
            f"Role: {self.role}\n"
            f"Goal: {self.goal}\n"
            f"{'Backstory: ' + self.backstory + chr(10) if self.backstory else ''}"
            f"Available tools: {', '.join(self.tools) if self.tools else 'none — respond with text only'}.\n\n"
            "Complete assigned tasks thoroughly. Be precise, concise, and actionable.\n"
            "When you have completed your task, start your final answer with 'DONE:'."
        )


class AgentNode(ABC):
    """Base class for all multi-agent nodes."""

    def __init__(
        self,
        agent_id: str | None = None,
        spec: AgentNodeSpec | None = None,
        session_id: str = "default",
    ):
        self.agent_id = agent_id or f"agent_{str(uuid.uuid4())[:8]}"
        self.spec = spec or AgentNodeSpec(name=self.agent_id, role="generic", goal="Process tasks")
        self.session_id = session_id
        self.created_at = time.time()
        self.message_count = 0
        self.task_count = 0
        self._inbox: asyncio.Queue = asyncio.Queue(maxsize=100)
        self._running = False

        # register on bus
        bus = AgentBus.get()
        bus.register_direct(self.agent_id, self._on_direct_message)
        for topic in self.spec.topics:
            bus.subscribe(topic, self.agent_id, self._on_topic_message)
        # all nodes subscribe to their own agent_id topic
        bus.subscribe(self.agent_id, self.agent_id, self._on_topic_message)

        logger.info("agent_node_created", agent_id=self.agent_id, role=self.spec.role, name=self.spec.name)

    # ── Sending ───────────────────────────────────────────────────────────────

    async def send(
        self,
        content: str,
        topic: str = "general",
        recipient_id: str | None = None,
        msg_type: str = "message",
        payload: dict | None = None,
        parent_msg_id: str | None = None,
    ) -> AgentMessage:
        msg = AgentMessage(
            sender_id=self.agent_id,
            sender_name=self.spec.name,
            recipient_id=recipient_id,
            topic=topic,
            content=content,
            payload=payload or {},
            msg_type=msg_type,
            parent_msg_id=parent_msg_id,
        )
        await AgentBus.get().publish(msg)
        return msg

    async def reply(self, original: AgentMessage, content: str, msg_type: str = "result") -> AgentMessage:
        return await self.send(
            content=content,
            topic=original.topic,
            recipient_id=original.sender_id,
            msg_type=msg_type,
            parent_msg_id=original.id,
        )

    # ── Receiving ─────────────────────────────────────────────────────────────

    async def _on_direct_message(self, msg: AgentMessage) -> None:
        self.message_count += 1
        await self._inbox.put(msg)
        await self.handle_message(msg)

    async def _on_topic_message(self, msg: AgentMessage) -> None:
        self.message_count += 1
        await self.handle_message(msg)

    @abstractmethod
    async def handle_message(self, msg: AgentMessage) -> None:
        """React to an incoming message."""
        ...

    @abstractmethod
    async def process_task(self, task: str, context: str = "", blackboard_key: str | None = None) -> str:
        """Execute a task and return output string."""
        ...

    # ── Blackboard helpers ────────────────────────────────────────────────────

    def bb_write(self, key: str, value: Any, tags: list[str] | None = None) -> None:
        board = BlackboardRegistry.get().get_or_create(self.session_id)
        board.write(key, value, author_id=self.agent_id, author_name=self.spec.name, tags=tags)

    def bb_read(self, key: str) -> Any:
        board = BlackboardRegistry.get().get_or_create(self.session_id)
        return board.read(key)

    def bb_context(self) -> str:
        board = BlackboardRegistry.get().get_or_create(self.session_id)
        return board.to_context_str()

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def deregister(self) -> None:
        bus = AgentBus.get()
        bus.unregister_direct(self.agent_id)
        for topic in self.spec.topics:
            bus.unsubscribe(topic, self.agent_id)
        bus.unsubscribe(self.agent_id, self.agent_id)

    def to_dict(self) -> dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "name": self.spec.name,
            "role": self.spec.role,
            "goal": self.spec.goal,
            "tools": self.spec.tools,
            "topics": self.spec.topics,
            "session_id": self.session_id,
            "message_count": self.message_count,
            "task_count": self.task_count,
            "created_at": self.created_at,
        }


# ── Concrete: LLM-backed agent node ──────────────────────────────────────────

class LLMAgentNode(AgentNode):
    """
    Agent node that uses the provider LLM to process tasks and reply to messages.
    Used by AgentFactory for dynamically created agents.
    """

    async def handle_message(self, msg: AgentMessage) -> None:
        """Auto-respond to task messages directed to this agent."""
        if msg.msg_type == "task" and msg.recipient_id == self.agent_id:
            await self.send(
                content=f"[{self.spec.name}] received task: {msg.content[:60]}…",
                topic=msg.topic,
                recipient_id=msg.sender_id,
                msg_type="status",
            )
            result = await self.process_task(msg.content, context=self.bb_context())
            await self.reply(msg, result, msg_type="result")

    async def process_task(self, task: str, context: str = "", blackboard_key: str | None = None) -> str:
        self.task_count += 1
        start = time.perf_counter()

        try:
            from app.providers.router import ProviderRouter
            pr = ProviderRouter.get()
            provider = pr.get_active_provider()
            if provider is None:
                return f"[{self.spec.name}] No LLM provider available."

            system = self.spec.to_system_prompt()
            if context:
                system += f"\n\n{context[:1500]}"

            res = await provider.chat(
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": task},
                ],
                model_id=self.spec.model_preference or "",
                max_tokens=self.spec.max_tokens,
            )
            output = res.get("choices", [{}])[0].get("message", {}).get("content", "") or ""

            elapsed = round((time.perf_counter() - start) * 1000, 1)
            logger.info("llm_agent_task_done", agent=self.spec.name, elapsed_ms=elapsed)

            # write result to blackboard if key given
            if blackboard_key and output:
                self.bb_write(blackboard_key, output, tags=["result"])

            # broadcast result to session topic
            await self.send(
                content=output[:300],
                topic=f"session_{self.session_id}",
                msg_type="result",
                payload={"full_output": output, "task": task[:100]},
            )
            return output

        except Exception as exc:
            logger.warning("llm_agent_task_error", agent=self.spec.name, error=str(exc))
            return f"[{self.spec.name}] Error: {exc}"


# ── Concrete: Echo agent (testing) ───────────────────────────────────────────

class EchoAgentNode(AgentNode):
    async def handle_message(self, msg: AgentMessage) -> None:
        if msg.msg_type == "task":
            await self.reply(msg, f"[Echo] {msg.content}", msg_type="result")

    async def process_task(self, task: str, context: str = "", blackboard_key: str | None = None) -> str:
        return f"[Echo:{self.spec.name}] {task}"
