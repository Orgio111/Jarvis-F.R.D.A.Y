"""
AgentFactory — dynamic agent creation system.

Capabilities:
  1. Create agents from explicit spec (AgentNodeSpec)
  2. LLM-driven spec generation: given a task description,
     the factory asks an LLM to design the optimal agent spec
  3. "Agent-to-generate-agent": a running agent can call
     factory.spawn_for_task() to create a sub-agent and delegate
  4. Registry of all live agents (by session)
  5. Auto-cleanup of idle agents

Agent-to-generate-agent flow:
    Orchestrator → factory.design_agent_for_task(task)
                 → LLM returns AgentNodeSpec JSON
                 → factory.spawn(spec)         → LLMAgentNode
                 → node.process_task(task)
                 → result returned to orchestrator
"""
from __future__ import annotations

import asyncio
import json
import time
import uuid
from dataclasses import asdict
from typing import Any

from app.core.logging import get_logger
from app.multi_agent.agent_node import AgentNode, AgentNodeSpec, LLMAgentNode
from app.multi_agent.agent_bus import AgentBus, AgentMessage

logger = get_logger(__name__)

# Predefined role templates — fast-path without LLM call
_ROLE_TEMPLATES: dict[str, dict] = {
    "coder": {
        "goal": "Write, debug, and improve code across multiple programming languages.",
        "backstory": "Elite software engineer with expertise in Python, JS, TS, Rust, Go, shell.",
        "tools": ["code_execute", "file_read", "file_write"],
    },
    "researcher": {
        "goal": "Gather accurate information from the web and synthesise clear summaries.",
        "backstory": "Meticulous research analyst who cross-references sources and flags uncertainty.",
        "tools": ["web_search", "browse_url", "memory_search"],
    },
    "devops": {
        "goal": "Manage infrastructure, containers, deployments, and system operations.",
        "backstory": "Senior DevOps engineer skilled in Docker, K8s, CI/CD, cloud infra.",
        "tools": ["shell_exec", "file_read", "file_write", "code_execute"],
    },
    "analyst": {
        "goal": "Analyse data, identify patterns, and produce clear insights.",
        "backstory": "Data scientist who writes pandas/numpy pipelines and explains findings clearly.",
        "tools": ["code_execute", "file_read"],
    },
    "writer": {
        "goal": "Produce high-quality written content: docs, reports, emails, long-form text.",
        "backstory": "Professional writer who adapts tone and structures content logically.",
        "tools": ["file_write", "memory_search"],
    },
    "orchestrator": {
        "goal": "Coordinate subtasks and synthesise results into a coherent final answer.",
        "backstory": "Manager agent that delegates to specialists and produces unified responses.",
        "tools": [],
    },
    "planner": {
        "goal": "Decompose complex goals into ordered subtasks with clear dependencies.",
        "backstory": "Strategic planner who creates actionable step-by-step execution plans.",
        "tools": [],
    },
    "reviewer": {
        "goal": "Review outputs for correctness, quality, and completeness.",
        "backstory": "Critical reviewer who spots errors, inconsistencies, and improvements.",
        "tools": [],
    },
}

_DESIGN_SYSTEM_PROMPT = """You are AgentDesigner — you create optimal AI agent specifications.

Given a task description, return a JSON object with this exact schema:
{
  "name": "AgentName (short, descriptive, PascalCase)",
  "role": "one of: coder|researcher|devops|analyst|writer|orchestrator|planner|reviewer|custom",
  "goal": "clear one-sentence goal for this agent",
  "backstory": "2-3 sentences describing this agent's expertise and approach",
  "tools": ["tool_id_1", "tool_id_2"],
  "topics": ["topic_to_subscribe"],
  "model_preference": "",
  "max_tokens": 1024
}

Available tools: code_execute, file_read, file_write, web_search, browse_url, memory_search, shell_exec
Return ONLY the JSON object, no explanation."""


class AgentRegistry:
    """Live registry of all spawned agents keyed by session."""

    _instance: AgentRegistry | None = None

    def __init__(self):
        # session_id → {agent_id: AgentNode}
        self._agents: dict[str, dict[str, AgentNode]] = {}

    @classmethod
    def get(cls) -> AgentRegistry:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def register(self, agent: AgentNode) -> None:
        sid = agent.session_id
        if sid not in self._agents:
            self._agents[sid] = {}
        self._agents[sid][agent.agent_id] = agent

    def get_agent(self, agent_id: str, session_id: str | None = None) -> AgentNode | None:
        if session_id:
            return self._agents.get(session_id, {}).get(agent_id)
        for agents in self._agents.values():
            if agent_id in agents:
                return agents[agent_id]
        return None

    def list_agents(self, session_id: str) -> list[dict]:
        return [a.to_dict() for a in self._agents.get(session_id, {}).values()]

    def list_all(self) -> list[dict]:
        result = []
        for agents in self._agents.values():
            result.extend(a.to_dict() for a in agents.values())
        return result

    def remove(self, agent_id: str, session_id: str) -> None:
        agents = self._agents.get(session_id, {})
        agent = agents.pop(agent_id, None)
        if agent:
            agent.deregister()

    def cleanup_session(self, session_id: str) -> None:
        agents = self._agents.pop(session_id, {})
        for agent in agents.values():
            agent.deregister()

    def total_count(self) -> int:
        return sum(len(v) for v in self._agents.values())


class AgentFactory:
    """
    Creates, registers, and manages AgentNodes.

    Key feature: design_agent_for_task() uses an LLM to generate
    the optimal agent spec for any given task — enabling true
    agent-to-generate-agent behaviour.
    """

    _instance: AgentFactory | None = None

    @classmethod
    def get(cls) -> AgentFactory:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    # ── Spawn from explicit spec ──────────────────────────────────────────────

    def spawn(self, spec: AgentNodeSpec, session_id: str = "default") -> LLMAgentNode:
        """Create and register an LLMAgentNode from a spec."""
        agent_id = f"{spec.role}_{str(uuid.uuid4())[:6]}"
        node = LLMAgentNode(agent_id=agent_id, spec=spec, session_id=session_id)
        AgentRegistry.get().register(node)
        logger.info("agent_factory_spawn", agent_id=agent_id, name=spec.name, role=spec.role, session=session_id)
        return node

    def spawn_from_role(self, role: str, session_id: str = "default", name: str | None = None) -> LLMAgentNode:
        """Fast-path: spawn from a predefined role template."""
        tmpl = _ROLE_TEMPLATES.get(role, _ROLE_TEMPLATES["orchestrator"])
        spec = AgentNodeSpec(
            name=name or f"{role.capitalize()}Agent",
            role=role,
            goal=tmpl["goal"],
            backstory=tmpl["backstory"],
            tools=tmpl["tools"],
            topics=[f"role_{role}"],
        )
        return self.spawn(spec, session_id)

    # ── LLM-driven spec design ────────────────────────────────────────────────

    async def design_agent_for_task(self, task: str) -> AgentNodeSpec:
        """
        Ask an LLM to design the optimal agent spec for a given task.
        Returns AgentNodeSpec. Falls back to orchestrator template on error.
        """
        # fast-path: keyword match to role template
        task_lower = task.lower()
        for role, tmpl in _ROLE_TEMPLATES.items():
            if role == "orchestrator":
                continue
            keywords = {
                "coder": ["code", "python", "script", "implement", "debug", "function"],
                "researcher": ["research", "search", "find", "what is", "explain", "summarize"],
                "devops": ["docker", "deploy", "server", "kubernetes", "infra", "shell"],
                "analyst": ["data", "analyse", "analyze", "chart", "csv", "statistics"],
                "writer": ["write", "document", "report", "email", "draft", "readme"],
                "planner": ["plan", "steps", "decompose", "strategy", "roadmap"],
                "reviewer": ["review", "check", "verify", "test", "quality"],
            }.get(role, [])
            if any(kw in task_lower for kw in keywords):
                spec = AgentNodeSpec(
                    name=f"{role.capitalize()}Agent",
                    role=role,
                    goal=tmpl["goal"],
                    backstory=tmpl["backstory"],
                    tools=tmpl["tools"],
                    topics=[f"role_{role}"],
                )
                logger.info("agent_factory_design_fast_path", role=role, task=task[:60])
                return spec

        # slow-path: LLM designs the agent
        try:
            from app.providers.router import ProviderRouter
            pr = ProviderRouter.get()
            provider = pr.get_active_provider()
            if provider is None:
                raise RuntimeError("No provider")

            res = await provider.chat(
                messages=[
                    {"role": "system", "content": _DESIGN_SYSTEM_PROMPT},
                    {"role": "user", "content": f"Design an agent for this task:\n{task}"},
                ],
                model_id="",
                max_tokens=512,
            )
            raw = res.get("choices", [{}])[0].get("message", {}).get("content", "") or ""

            # extract JSON
            import re
            match = re.search(r"\{[\s\S]*\}", raw)
            if match:
                data = json.loads(match.group())
                spec = AgentNodeSpec(
                    name=data.get("name", "CustomAgent"),
                    role=data.get("role", "custom"),
                    goal=data.get("goal", task[:100]),
                    backstory=data.get("backstory", ""),
                    tools=data.get("tools", []),
                    topics=data.get("topics", []),
                    model_preference=data.get("model_preference", ""),
                    max_tokens=int(data.get("max_tokens", 1024)),
                )
                logger.info("agent_factory_design_llm", name=spec.name, role=spec.role)
                return spec

        except Exception as exc:
            logger.warning("agent_factory_design_error", error=str(exc))

        # ultimate fallback
        return AgentNodeSpec(
            name="GeneralistAgent",
            role="orchestrator",
            goal=f"Complete the task: {task[:80]}",
            backstory=_ROLE_TEMPLATES["orchestrator"]["backstory"],
        )

    # ── Agent-to-generate-agent entry point ───────────────────────────────────

    async def spawn_for_task(
        self,
        task: str,
        session_id: str = "default",
        auto_run: bool = True,
        blackboard_key: str | None = None,
    ) -> tuple[LLMAgentNode, str]:
        """
        Design + spawn + optionally run an agent for a task.
        Returns (agent_node, output_string).
        The agent remains registered after execution (caller can reuse).
        """
        spec = await self.design_agent_for_task(task)
        node = self.spawn(spec, session_id)

        # announce creation on bus
        bus = AgentBus.get()
        await bus.publish(AgentMessage(
            sender_id="agent_factory",
            sender_name="AgentFactory",
            topic=f"session_{session_id}",
            content=f"Spawned [{node.spec.name}] ({node.spec.role}) for task: {task[:80]}",
            msg_type="status",
            payload={"agent": node.to_dict()},
        ))

        output = ""
        if auto_run:
            output = await node.process_task(task, blackboard_key=blackboard_key or f"result_{node.agent_id}")

        return node, output

    def get_registry(self) -> AgentRegistry:
        return AgentRegistry.get()

    def get_status(self) -> dict[str, Any]:
        reg = AgentRegistry.get()
        return {
            "total_agents": reg.total_count(),
            "sessions": reg.list_all(),
            "role_templates": list(_ROLE_TEMPLATES.keys()),
        }
