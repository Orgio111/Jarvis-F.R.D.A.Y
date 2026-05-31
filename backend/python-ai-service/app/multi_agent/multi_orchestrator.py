"""
MultiAgentOrchestrator — coordinates multi-agent execution.

Supports all 4 patterns:
  1. Hub-and-spoke: Orchestrator agent breaks task → assigns to specialists → aggregates
  2. Pipeline/chain: A → B → C (output of each feeds next)
  3. Parallel: multiple agents run simultaneously, results merged
  4. Dynamic: orchestrator decides pattern per task using LLM

All patterns:
  - Announce start/step/end on AgentBus (SSE visible to UI)
  - Write intermediate results to SharedBlackboard
  - Spawned agents are tracked in AgentRegistry

Usage:
    orch = MultiAgentOrchestrator(session_id="abc123")
    result = await orch.run(task="Build a REST API in Python")
"""
from __future__ import annotations

import asyncio
import json
import re
import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from app.core.logging import get_logger
from app.multi_agent.agent_bus import AgentBus, AgentMessage
from app.multi_agent.agent_factory import AgentFactory
from app.multi_agent.agent_node import AgentNodeSpec, LLMAgentNode
from app.multi_agent.blackboard import BlackboardRegistry

logger = get_logger(__name__)

_DECOMPOSE_PROMPT = """You are a task decomposition expert.

Given a complex task, break it into 2-5 subtasks. Each subtask should be:
- Specific and actionable
- Assigned to the best role
- Independent OR chained (specify if output of one feeds another)

Return JSON:
{
  "pattern": "parallel" | "chain" | "hub_spoke",
  "subtasks": [
    {
      "id": "step_1",
      "description": "specific subtask description",
      "role": "coder|researcher|devops|analyst|writer|planner|reviewer",
      "depends_on": [],
      "blackboard_key": "step_1_result"
    }
  ],
  "aggregation_hint": "how to combine results"
}

Return ONLY JSON."""

_AGGREGATE_PROMPT = """You are a synthesis expert. 
Given multiple agent outputs, produce a single coherent, well-structured final answer.
Be concise. Remove redundancy. Preserve all important information."""


@dataclass
class SubtaskResult:
    step_id: str
    description: str
    role: str
    agent_id: str
    agent_name: str
    output: str
    success: bool
    elapsed_ms: float
    blackboard_key: str = ""


@dataclass
class MultiAgentResult:
    session_id: str
    task: str
    pattern: str
    subtasks: list[SubtaskResult]
    final_output: str
    success: bool
    total_elapsed_ms: float
    agent_count: int
    error: str | None = None
    blackboard_snapshot: dict = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "task": self.task,
            "pattern": self.pattern,
            "subtasks": [
                {
                    "step_id": s.step_id,
                    "description": s.description,
                    "role": s.role,
                    "agent_id": s.agent_id,
                    "agent_name": s.agent_name,
                    "output": s.output[:500],
                    "success": s.success,
                    "elapsed_ms": s.elapsed_ms,
                }
                for s in self.subtasks
            ],
            "final_output": self.final_output,
            "success": self.success,
            "total_elapsed_ms": self.total_elapsed_ms,
            "agent_count": self.agent_count,
            "error": self.error,
        }


class MultiAgentOrchestrator:
    """
    Main entry point for multi-agent task execution.

    For each task:
      1. Decompose task (LLM → subtasks + pattern)
      2. Spawn specialist agents via AgentFactory
      3. Execute with chosen pattern
      4. Aggregate results
      5. Clean up spawned agents (optional)
    """

    def __init__(self, session_id: str | None = None):
        self.session_id = session_id or str(uuid.uuid4())[:12]
        self._factory = AgentFactory.get()
        self._bus = AgentBus.get()
        self._board = BlackboardRegistry.get().get_or_create(self.session_id)

    async def _announce(self, content: str, msg_type: str = "status", payload: dict | None = None) -> None:
        await self._bus.publish(AgentMessage(
            sender_id="multi_orchestrator",
            sender_name="MultiOrchestrator",
            topic=f"session_{self.session_id}",
            content=content,
            msg_type=msg_type,
            payload=payload or {},
        ))

    # ── Main entry ────────────────────────────────────────────────────────────

    async def run(
        self,
        task: str,
        pattern: str = "auto",   # auto | parallel | chain | hub_spoke
        max_agents: int = 6,
        cleanup: bool = True,
    ) -> MultiAgentResult:
        start = time.perf_counter()
        await self._announce(f"Starting multi-agent execution for: {task[:80]}", msg_type="status")

        subtask_results: list[SubtaskResult] = []
        spawned: list[LLMAgentNode] = []
        used_pattern = pattern
        error_msg = None

        try:
            # 1. Decompose
            decomp = await self._decompose_task(task, pattern)
            used_pattern = decomp.get("pattern", "parallel")
            subtasks = decomp.get("subtasks", [])[:max_agents]
            aggregation_hint = decomp.get("aggregation_hint", "")

            if not subtasks:
                # Single agent fallback
                _, output = await self._factory.spawn_for_task(task, session_id=self.session_id)
                elapsed = round((time.perf_counter() - start) * 1000, 1)
                return MultiAgentResult(
                    session_id=self.session_id,
                    task=task,
                    pattern="single",
                    subtasks=[],
                    final_output=output,
                    success=bool(output),
                    total_elapsed_ms=elapsed,
                    agent_count=1,
                )

            await self._announce(
                f"Decomposed into {len(subtasks)} subtasks, pattern={used_pattern}",
                payload={"subtasks": subtasks, "pattern": used_pattern},
            )

            # 2. Spawn agents for each subtask
            agents: dict[str, LLMAgentNode] = {}
            for st in subtasks:
                spec = AgentNodeSpec(
                    name=f"{st['role'].capitalize()}Agent_{st['id']}",
                    role=st["role"],
                    goal=st["description"],
                    backstory=self._role_backstory(st["role"]),
                    tools=self._role_tools(st["role"]),
                    topics=[f"session_{self.session_id}"],
                )
                node = self._factory.spawn(spec, session_id=self.session_id)
                agents[st["id"]] = node
                spawned.append(node)

            # 3. Execute with pattern
            if used_pattern == "chain":
                subtask_results = await self._run_chain(task, subtasks, agents)
            elif used_pattern == "hub_spoke":
                subtask_results = await self._run_hub_spoke(task, subtasks, agents)
            else:  # parallel (default)
                subtask_results = await self._run_parallel(task, subtasks, agents)

            # 4. Aggregate
            final_output = await self._aggregate(task, subtask_results, aggregation_hint)
            self._board.write("final_output", final_output, author_id="multi_orchestrator",
                              author_name="MultiOrchestrator", tags=["final"])

            await self._announce("Multi-agent execution complete.", msg_type="result",
                                  payload={"output": final_output[:300]})

        except Exception as exc:
            logger.warning("multi_orchestrator_error", error=str(exc))
            error_msg = str(exc)
            final_output = f"Execution failed: {exc}"

        finally:
            if cleanup:
                for node in spawned:
                    AgentFactory.get().get_registry().remove(node.agent_id, self.session_id)

        elapsed = round((time.perf_counter() - start) * 1000, 1)
        return MultiAgentResult(
            session_id=self.session_id,
            task=task,
            pattern=used_pattern,
            subtasks=subtask_results,
            final_output=final_output if 'final_output' in dir() else "",
            success=error_msg is None and bool(subtask_results),
            total_elapsed_ms=elapsed,
            agent_count=len(spawned),
            error=error_msg,
            blackboard_snapshot=self._board.snapshot(),
        )

    # ── Execution patterns ────────────────────────────────────────────────────

    async def _run_parallel(
        self,
        task: str,
        subtasks: list[dict],
        agents: dict[str, LLMAgentNode],
    ) -> list[SubtaskResult]:
        """Run all subtasks simultaneously, wait for all."""
        await self._announce("Running subtasks in parallel...", msg_type="status")

        async def run_one(st: dict) -> SubtaskResult:
            node = agents[st["id"]]
            t0 = time.perf_counter()
            await self._announce(
                f"→ [{node.spec.name}] starting: {st['description'][:60]}",
                msg_type="status",
            )
            output = await node.process_task(
                st["description"],
                context=f"Overall task: {task}\n{self._board.to_context_str(10)}",
                blackboard_key=st.get("blackboard_key", f"{st['id']}_result"),
            )
            elapsed = round((time.perf_counter() - t0) * 1000, 1)
            await self._announce(
                f"✓ [{node.spec.name}] done in {elapsed}ms",
                msg_type="result",
                payload={"step_id": st["id"], "output": output[:200]},
            )
            return SubtaskResult(
                step_id=st["id"],
                description=st["description"],
                role=st["role"],
                agent_id=node.agent_id,
                agent_name=node.spec.name,
                output=output,
                success=bool(output),
                elapsed_ms=elapsed,
                blackboard_key=st.get("blackboard_key", ""),
            )

        results = await asyncio.gather(*[run_one(st) for st in subtasks], return_exceptions=False)
        return list(results)

    async def _run_chain(
        self,
        task: str,
        subtasks: list[dict],
        agents: dict[str, LLMAgentNode],
    ) -> list[SubtaskResult]:
        """Run subtasks sequentially, feeding output of each to the next."""
        await self._announce("Running subtasks as pipeline chain...", msg_type="status")
        results: list[SubtaskResult] = []
        prev_output = ""

        for st in subtasks:
            node = agents[st["id"]]
            t0 = time.perf_counter()
            context = f"Overall task: {task}\n"
            if prev_output:
                context += f"\nPrevious agent output:\n{prev_output[:800]}"
            context += f"\n{self._board.to_context_str(10)}"

            await self._announce(
                f"→ [{node.spec.name}] chained step: {st['description'][:60]}",
                msg_type="status",
            )
            output = await node.process_task(
                st["description"],
                context=context,
                blackboard_key=st.get("blackboard_key", f"{st['id']}_result"),
            )
            elapsed = round((time.perf_counter() - t0) * 1000, 1)
            await self._announce(
                f"✓ [{node.spec.name}] chain step done",
                msg_type="result",
                payload={"step_id": st["id"], "output": output[:200]},
            )
            results.append(SubtaskResult(
                step_id=st["id"],
                description=st["description"],
                role=st["role"],
                agent_id=node.agent_id,
                agent_name=node.spec.name,
                output=output,
                success=bool(output),
                elapsed_ms=elapsed,
                blackboard_key=st.get("blackboard_key", ""),
            ))
            prev_output = output  # chain: pass to next

        return results

    async def _run_hub_spoke(
        self,
        task: str,
        subtasks: list[dict],
        agents: dict[str, LLMAgentNode],
    ) -> list[SubtaskResult]:
        """
        Hub-and-spoke: orchestrator assigns tasks, waits for all,
        then optionally routes follow-up tasks based on results.
        First pass is parallel; then orchestrator reviews and optionally
        spawns additional agents.
        """
        await self._announce("Running hub-and-spoke pattern...", msg_type="status")

        # First pass: all specialists in parallel (same as parallel but with hub framing)
        results = await self._run_parallel(task, subtasks, agents)

        # Hub review: check if any result needs follow-up
        failed = [r for r in results if not r.success]
        if failed:
            for fr in failed[:2]:  # retry up to 2 failed steps
                await self._announce(
                    f"Hub retrying failed step [{fr.description[:40]}]...",
                    msg_type="status",
                )
                node, retry_output = await self._factory.spawn_for_task(
                    fr.description,
                    session_id=self.session_id,
                    auto_run=True,
                )
                fr.output = retry_output
                fr.success = bool(retry_output)

        return results

    # ── Decomposition ─────────────────────────────────────────────────────────

    async def _decompose_task(self, task: str, hint_pattern: str = "auto") -> dict:
        """Ask LLM to decompose task into subtasks with pattern."""
        try:
            from app.providers.router import ProviderRouter
            pr = ProviderRouter.get()
            provider = pr.get_active_provider()
            if provider is None:
                raise RuntimeError("No provider")

            hint = f"\nPreferred pattern: {hint_pattern}" if hint_pattern != "auto" else ""
            res = await provider.chat(
                messages=[
                    {"role": "system", "content": _DECOMPOSE_PROMPT},
                    {"role": "user", "content": f"Task: {task}{hint}"},
                ],
                model_id="",
                max_tokens=600,
            )
            raw = res.get("choices", [{}])[0].get("message", {}).get("content", "") or ""
            match = re.search(r"\{[\s\S]*\}", raw)
            if match:
                return json.loads(match.group())
        except Exception as exc:
            logger.warning("multi_orch_decompose_error", error=str(exc))

        # fallback: single subtask
        return {
            "pattern": "parallel",
            "subtasks": [
                {
                    "id": "step_1",
                    "description": task,
                    "role": "orchestrator",
                    "depends_on": [],
                    "blackboard_key": "step_1_result",
                }
            ],
            "aggregation_hint": "Use the output directly.",
        }

    # ── Aggregation ───────────────────────────────────────────────────────────

    async def _aggregate(
        self,
        task: str,
        results: list[SubtaskResult],
        hint: str = "",
    ) -> str:
        if not results:
            return ""
        if len(results) == 1:
            return results[0].output

        outputs_text = "\n\n".join(
            f"=== {r.agent_name} ({r.role}) ===\n{r.output}"
            for r in results if r.output
        )
        if not outputs_text:
            return "All agents returned empty output."

        try:
            from app.providers.router import ProviderRouter
            pr = ProviderRouter.get()
            provider = pr.get_active_provider()
            if provider is None:
                return outputs_text

            user_msg = (
                f"Original task: {task}\n\n"
                f"Agent outputs:\n{outputs_text[:3000]}\n\n"
                f"{'Aggregation note: ' + hint if hint else ''}"
            )
            res = await provider.chat(
                messages=[
                    {"role": "system", "content": _AGGREGATE_PROMPT},
                    {"role": "user", "content": user_msg},
                ],
                model_id="",
                max_tokens=1500,
            )
            return res.get("choices", [{}])[0].get("message", {}).get("content", "") or outputs_text
        except Exception as exc:
            logger.warning("multi_orch_aggregate_error", error=str(exc))
            return outputs_text

    # ── Helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _role_backstory(role: str) -> str:
        backstories = {
            "coder": "Elite software engineer with expertise in Python, JS, TS, Rust, Go, shell.",
            "researcher": "Meticulous research analyst who cross-references sources and flags uncertainty.",
            "devops": "Senior DevOps engineer skilled in Docker, K8s, CI/CD, cloud infra.",
            "analyst": "Data scientist who writes pandas/numpy pipelines and explains findings clearly.",
            "writer": "Professional writer who adapts tone and structures content logically.",
            "planner": "Strategic planner who creates actionable execution plans.",
            "reviewer": "Critical reviewer who spots errors, inconsistencies, and improvements.",
        }
        return backstories.get(role, "Specialist AI agent focused on completing tasks effectively.")

    @staticmethod
    def _role_tools(role: str) -> list[str]:
        tools = {
            "coder": ["code_execute", "file_read", "file_write"],
            "researcher": ["web_search", "browse_url", "memory_search"],
            "devops": ["shell_exec", "file_read", "file_write", "code_execute"],
            "analyst": ["code_execute", "file_read"],
            "writer": ["file_write", "memory_search"],
        }
        return tools.get(role, [])
