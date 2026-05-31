"""
ObsidianSync — singleton service that manages the vault writer and all loggers.

Usage (anywhere in the backend):
    from app.obsidian.sync import get_obsidian

    obs = get_obsidian()
    if obs:
        await obs.agent.log("coder", "Completed file edit", detail="Added 42 lines")
        await obs.decision.log("Use GPT-4o for code task", agent_id="coder", outcome="success")
        await obs.memory.log_short_term("User prefers Python", source="chat")
        await obs.task.log_start("t-abc123", "Refactor auth module")
        await obs.improvement.log_win("Act as a senior engineer...", outcome="clean code")

Hook into orchestrator events with register_hooks().
"""
from __future__ import annotations

import asyncio
import logging
import os
from typing import TYPE_CHECKING

from app.obsidian.writer import ObsidianWriter
from app.obsidian.logger import (
    AgentDiaryLogger,
    DecisionLogger,
    MemoryLogger,
    TaskLogger,
    SelfImprovementLogger,
)

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

_DEFAULT_VAULT = os.path.join(os.path.dirname(__file__), "../../../../data/obsidian_vault")


class ObsidianSync:
    """
    Central facade for all Obsidian logging.
    Exposes .agent, .decision, .memory, .task, .improvement loggers.
    """

    def __init__(self, vault_root: str):
        self._writer = ObsidianWriter(vault_root)
        self.agent = AgentDiaryLogger(self._writer)
        self.decision = DecisionLogger(self._writer)
        self.memory = MemoryLogger(self._writer)
        self.task = TaskLogger(self._writer)
        self.improvement = SelfImprovementLogger(self._writer)
        self.vault_root = vault_root
        logger.info(f"ObsidianSync initialised — vault: {vault_root}")

    def writer(self) -> ObsidianWriter:
        return self._writer


# ── Singleton ─────────────────────────────────────────────────────────────────

_instance: ObsidianSync | None = None


def get_obsidian(vault_root: str | None = None) -> ObsidianSync | None:
    """
    Returns the process-wide ObsidianSync singleton.
    Returns None if obsidian is disabled (OBSIDIAN_ENABLED=false).
    First call with vault_root initialises the singleton.
    """
    global _instance
    if _instance is not None:
        return _instance

    enabled = os.environ.get("OBSIDIAN_ENABLED", "true").lower() not in ("false", "0", "no")
    if not enabled:
        return None

    root = vault_root or os.environ.get("OBSIDIAN_VAULT_PATH", _DEFAULT_VAULT)
    os.makedirs(root, exist_ok=True)

    try:
        _instance = ObsidianSync(root)
    except Exception as exc:
        logger.error(f"ObsidianSync init failed: {exc}")
        return None

    return _instance


# ── Orchestrator hook registration ────────────────────────────────────────────

def register_hooks():
    """
    Attach Obsidian logging hooks to orchestrator events.
    Call once at app startup (after get_obsidian() is initialised).
    """
    obs = get_obsidian()
    if obs is None:
        return

    try:
        from app.agents.orchestrator import Orchestrator

        @Orchestrator.on("step_complete")
        async def _on_step(event: dict):
            step_id = event.get("step_id", "unknown")
            agent = event.get("agent", "orchestrator")
            task = event.get("task", "")
            success = event.get("success", True)
            duration = event.get("duration_ms")

            await obs.agent.log(
                agent,
                "Step complete" if success else "Step failed",
                detail=task[:200],
                metadata={"step": step_id, "duration_ms": duration or "?"},
                tags=["step"],
            )
            await obs.task.log_complete(
                step_id,
                success=success,
                duration_ms=duration,
                summary=task[:120],
            )

        @Orchestrator.on("task_start")
        async def _on_task_start(event: dict):
            await obs.task.log_start(
                event.get("task_id", "?"),
                event.get("task", ""),
                agent_id=event.get("agent"),
            )

        @Orchestrator.on("decision")
        async def _on_decision(event: dict):
            await obs.decision.log(
                event.get("decision", ""),
                agent_id=event.get("agent"),
                task_id=event.get("task_id"),
                reasoning=event.get("reasoning", ""),
                outcome=event.get("outcome", "pending"),
                confidence=event.get("confidence"),
            )

        logger.info("Obsidian hooks registered on Orchestrator")

    except (ImportError, AttributeError) as exc:
        # Orchestrator may not support .on() yet — hooks are optional
        logger.debug(f"Obsidian orchestrator hooks skipped: {exc}")

    try:
        from app.services.self_improvement_loop import SelfImprovementLoop

        @SelfImprovementLoop.on("cycle_complete")
        async def _on_cycle(event: dict):
            if event.get("score", 0) >= 0.75:
                await obs.improvement.log_win(
                    prompt=event.get("prompt", ""),
                    outcome=event.get("summary", ""),
                    model=event.get("model", ""),
                    score=event.get("score"),
                    agent_id=event.get("agent"),
                )
            else:
                await obs.improvement.log_failure(
                    prompt=event.get("prompt", ""),
                    failure_reason=event.get("summary", "score too low"),
                    model=event.get("model", ""),
                    retry_count=event.get("retry_count", 0),
                    agent_id=event.get("agent"),
                )

        logger.info("Obsidian hooks registered on SelfImprovementLoop")

    except (ImportError, AttributeError) as exc:
        logger.debug(f"Obsidian self-improvement hooks skipped: {exc}")
