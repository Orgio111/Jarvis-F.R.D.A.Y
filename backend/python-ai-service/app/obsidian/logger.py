"""
ObsidianLogger — structured loggers that write Jarvis events to the Obsidian vault.

Loggers:
  AgentDiaryLogger       — per-agent daily diary (what each agent did)
  DecisionLogger         — swarm-level decision log with links
  MemoryLogger           — short/long-term memory snapshots
  TaskLogger             — task execution timeline
  SelfImprovementLogger  — prompt wins/failures tracking
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Literal

from app.obsidian.writer import ObsidianWriter, _today, _wikilink

logger = logging.getLogger(__name__)


def _now_ts() -> str:
    return datetime.now(timezone.utc).strftime("%H:%M:%S UTC")


class AgentDiaryLogger:
    """
    Per-agent daily diary.
    Path: agents/{agent_id}/YYYY-MM-DD.md
    """

    def __init__(self, writer: ObsidianWriter):
        self._w = writer

    async def log(
        self,
        agent_id: str,
        event: str,
        detail: str = "",
        metadata: dict[str, Any] | None = None,
        tags: list[str] | None = None,
    ):
        rel = f"agents/{agent_id}/{_today()}.md"
        meta_lines = ""
        if metadata:
            meta_lines = "\n".join(f"- **{k}**: `{v}`" for k, v in metadata.items())
            meta_lines = "\n\n**Context:**\n" + meta_lines

        body = f"**[{_now_ts()}]** {event}"
        if detail:
            body += f"\n\n{detail}"
        body += meta_lines

        await self._w.log_entry(
            rel,
            body=body,
            tags=(tags or []) + ["agent", "diary", agent_id],
        )

        # Also update live agent registry
        await self._update_registry(agent_id, event)

    async def _update_registry(self, agent_id: str, last_event: str):
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        content = (
            f"- **Last active**: {ts}\n"
            f"- **Last event**: {last_event}\n"
            f"- **Diary**: {_wikilink(f'agents/{agent_id}/{_today()}')}\n"
        )
        await self._w.upsert_section("swarm/agents.md", agent_id, content)


class DecisionLogger:
    """
    Swarm-level decision log.
    Path: swarm/decisions.md
    """

    def __init__(self, writer: ObsidianWriter):
        self._w = writer

    async def log(
        self,
        decision: str,
        agent_id: str | None = None,
        task_id: str | None = None,
        reasoning: str = "",
        outcome: Literal["pending", "success", "failed", "skipped"] = "pending",
        confidence: float | None = None,
        links: list[str] | None = None,
    ):
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        outcome_emoji = {
            "pending": "🔄",
            "success": "✅",
            "failed": "❌",
            "skipped": "⏭️",
        }.get(outcome, "❓")

        parts = [f"**Decision**: {decision}", f"**Outcome**: {outcome_emoji} {outcome}"]
        if agent_id:
            parts.append(f"**Agent**: {_wikilink(f'agents/{agent_id}/{_today()}', agent_id)}")
        if task_id:
            parts.append(f"**Task**: `{task_id}`")
        if confidence is not None:
            parts.append(f"**Confidence**: {confidence:.0%}")
        if reasoning:
            parts.append(f"\n**Reasoning**:\n> {reasoning}")
        if links:
            parts.append("**Related**: " + " | ".join(_wikilink(l) for l in links))

        body = "\n".join(parts)
        await self._w.log_entry(
            "swarm/decisions.md",
            body=body,
            heading=f"{ts} — {decision[:60]}",
            tags=["decision", "swarm", outcome],
        )


class MemoryLogger:
    """
    Memory snapshot logger.
    - Short-term: rolling last-50 entries
    - Long-term: crystallised facts (append-only)
    """

    def __init__(self, writer: ObsidianWriter):
        self._w = writer
        self._short_term_buffer: list[str] = []
        self._short_term_max = 50

    async def log_short_term(
        self,
        content: str,
        source: str = "agent",
        session_id: str | None = None,
    ):
        ts = _now_ts()
        entry = f"- `[{ts}]` **{source}**: {content}"
        if session_id:
            entry += f" _(session: `{session_id}`)_"

        self._short_term_buffer.append(entry)
        if len(self._short_term_buffer) > self._short_term_max:
            self._short_term_buffer = self._short_term_buffer[-self._short_term_max:]

        # Rewrite the entire short-term file (rolling window)
        lines = "\n".join(self._short_term_buffer)
        content_md = (
            f"---\n"
            f"title: Short-term Memory\n"
            f"updated: {datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}\n"
            f"tags: [memory, short-term]\n"
            f"---\n\n"
            f"# 🧠 Short-term Memory\n\n"
            f"_Last {self._short_term_max} entries — auto-updated_\n\n"
            f"## Entries\n\n"
            f"{lines}\n"
        )
        await self._w.overwrite("memory/short_term.md", content_md)

    async def log_long_term(
        self,
        fact: str,
        category: str = "general",
        confidence: float = 1.0,
        source_agent: str | None = None,
    ):
        confidence_bar = "█" * int(confidence * 5) + "░" * (5 - int(confidence * 5))
        body = (
            f"**Fact**: {fact}\n"
            f"**Category**: `{category}`\n"
            f"**Confidence**: `{confidence_bar}` {confidence:.0%}"
        )
        if source_agent:
            body += f"\n**Source**: {_wikilink(f'agents/{source_agent}/{_today()}', source_agent)}"

        await self._w.log_entry(
            "memory/long_term.md",
            body=body,
            tags=["memory", "long-term", category],
        )

    async def log_search_result(
        self,
        query: str,
        results: list[dict[str, Any]],
        layer: str = "recall",
    ):
        hits = "\n".join(
            f"- `{r.get('score', 0):.3f}` {r.get('content', '')[:120]}"
            for r in results[:10]
        )
        body = f"**Query**: `{query}`\n**Layer**: `{layer}`\n\n**Hits:**\n{hits}"
        await self._w.log_entry(
            "memory/search_index.md",
            body=body,
            tags=["memory", "search"],
        )


class TaskLogger:
    """
    Task execution timeline.
    Path: tasks/YYYY-MM-DD.md
    """

    def __init__(self, writer: ObsidianWriter):
        self._w = writer

    async def log_start(
        self,
        task_id: str,
        task: str,
        agent_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ):
        body_parts = [
            f"**Task**: {task}",
            f"**ID**: `{task_id}`",
            f"**Status**: 🔄 running",
        ]
        if agent_id:
            body_parts.append(
                f"**Agent**: {_wikilink(f'agents/{agent_id}/{_today()}', agent_id)}"
            )
        if metadata:
            for k, v in metadata.items():
                body_parts.append(f"**{k}**: `{v}`")

        await self._w.log_entry(
            f"tasks/{_today()}.md",
            body="\n".join(body_parts),
            heading=f"▶ {task_id[:8]} — {task[:60]}",
            tags=["task", "running"],
        )

    async def log_complete(
        self,
        task_id: str,
        success: bool,
        duration_ms: int | None = None,
        summary: str = "",
        error: str | None = None,
    ):
        status = "✅ success" if success else "❌ failed"
        body_parts = [
            f"**Task ID**: `{task_id}`",
            f"**Status**: {status}",
        ]
        if duration_ms is not None:
            body_parts.append(f"**Duration**: `{duration_ms}ms`")
        if summary:
            body_parts.append(f"**Summary**: {summary}")
        if error:
            body_parts.append(f"**Error**: ```\n{error}\n```")

        heading = ("✅" if success else "❌") + f" {task_id[:8]} — complete"
        await self._w.log_entry(
            f"tasks/{_today()}.md",
            body="\n".join(body_parts),
            heading=heading,
            tags=["task", "success" if success else "failed"],
        )


class SelfImprovementLogger:
    """
    Tracks what worked and what failed for self-improvement loop.
    Paths: self_improvement/prompt_wins.md, prompt_failures.md
    """

    def __init__(self, writer: ObsidianWriter):
        self._w = writer

    async def log_win(
        self,
        prompt: str,
        outcome: str,
        model: str = "",
        score: float | None = None,
        agent_id: str | None = None,
        tags: list[str] | None = None,
    ):
        score_str = f" (score: `{score:.2f}`)" if score is not None else ""
        body = f"**Prompt**:\n```\n{prompt[:500]}\n```\n\n**Outcome**: {outcome}{score_str}"
        if model:
            body += f"\n**Model**: `{model}`"
        if agent_id:
            body += f"\n**Agent**: {_wikilink(f'agents/{agent_id}/{_today()}', agent_id)}"

        await self._w.log_entry(
            "self_improvement/prompt_wins.md",
            body=body,
            tags=["prompt", "win"] + (tags or []),
        )

    async def log_failure(
        self,
        prompt: str,
        failure_reason: str,
        model: str = "",
        retry_count: int = 0,
        agent_id: str | None = None,
        tags: list[str] | None = None,
    ):
        body = (
            f"**Prompt**:\n```\n{prompt[:500]}\n```\n\n"
            f"**Failure**: {failure_reason}\n"
            f"**Retries**: `{retry_count}`"
        )
        if model:
            body += f"\n**Model**: `{model}`"
        if agent_id:
            body += f"\n**Agent**: {_wikilink(f'agents/{agent_id}/{_today()}', agent_id)}"

        await self._w.log_entry(
            "self_improvement/prompt_failures.md",
            body=body,
            tags=["prompt", "failure"] + (tags or []),
        )
