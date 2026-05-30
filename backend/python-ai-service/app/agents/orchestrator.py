"""Orchestrator — drives the full multi-agent pipeline for a coding task.

Pipeline:
  0. SpecAgent       — write spec/PRD with acceptance criteria (new)
  1. FilePickerAgent — find relevant files
  2. PlannerAgent    — decompose into steps (with dependency graph)
  3. Execute steps:
     - Group steps with no unmet depends_on → asyncio.gather() them in parallel
     - Sequential for dependent steps
     - Each step dispatched to the correct specialized agent
     - Retry-on-failure: up to _STEP_MAX_RETRIES before marking failed (new)
  4. ReviewerAgent   — review all edits from editor steps
  5. Yield SSE events throughout

Context compression is applied before passing history to Planner and per-step agents.

Usage:
    async for event in Orchestrator.run(task, file_tree, history, repo_root):
        yield event  # dict — see _emit()
"""
from __future__ import annotations

import asyncio
import os
from pathlib import Path
from typing import Any, AsyncIterator

from app.agents.context_compressor import compress
from app.agents.free_model_pool import AgentRole
from app.agents.specialized.editor import EditorAgent
from app.agents.specialized.file_picker import FilePickerAgent
from app.agents.specialized.planner import PlannerAgent
from app.agents.specialized.reviewer import ReviewerAgent
from app.agents.specialized.spec_agent import SpecAgent
from app.agents.specialized.terminal import TerminalAgent
from app.core.logging import get_logger

_STEP_MAX_RETRIES = 3   # retry each step up to this many times on failure
_RETRY_DELAY_S    = 2.0 # seconds between retries (exponential: *2 each attempt)

logger = get_logger(__name__)

Event = dict[str, Any]

_AGENT_MAP: dict[str, type] = {
    "editor":      EditorAgent,
    "terminal":    TerminalAgent,
    "reviewer":    ReviewerAgent,
    "file_picker": FilePickerAgent,
}


def _emit(event_type: str, data: dict[str, Any]) -> Event:
    return {"event": event_type, "data": data}


async def _load_file(path: str, repo_root: str, max_bytes: int = 8000) -> str:
    full = os.path.join(repo_root, path)
    try:
        with open(full, "r", errors="replace") as f:
            content = f.read(max_bytes)
        return content
    except OSError:
        return ""


class Orchestrator:
    """Stateless — instantiate per request."""

    def __init__(self, repo_root: str = "."):
        self.repo_root = repo_root

    async def run(
        self,
        task: str,
        file_tree: str = "",
        history: list[dict[str, str]] | None = None,
        max_files: int = 10,
    ) -> AsyncIterator[Event]:
        """Async generator yielding SSE-style event dicts."""
        history = history or []
        all_edits: list[dict[str, Any]] = []   # accumulated across editor steps
        step_results: dict[str, Any] = {}       # step_id → AgentResult

        # ── Step 0a: Compress history ─────────────────────────────────────────
        yield _emit("status", {"message": "Compressing context...", "phase": "compress"})
        compressed_history = await compress(history)

        # ── Step 0b: SpecAgent — write spec before planning ──────────────────
        yield _emit("status", {"message": "Writing spec...", "phase": "spec"})
        spec_agent = SpecAgent()
        spec_result = await spec_agent.run({
            "task": task,
            "files": [],
            "file_contents": {},
            "history": compressed_history,
        })
        yield _emit("agent_result", spec_result.to_dict())
        spec_text: str = spec_result.data.get("spec", "")
        spec_constraints: list[str] = spec_result.data.get("constraints", [])

        # ── Step 1: FilePicker ───────────────────────────────────────────────
        yield _emit("status", {"message": "Scanning codebase...", "phase": "file_picker"})
        fp_agent = FilePickerAgent()
        fp_result = await fp_agent.run({
            "task": task,
            "file_tree": file_tree,
            "max_files": max_files,
        })
        yield _emit("agent_result", fp_result.to_dict())

        relevant_files: list[str] = fp_result.data.get("files", [])

        # ── Step 2: Load file contents ────────────────────────────────────────
        yield _emit("status", {"message": f"Loading {len(relevant_files)} files...", "phase": "load_files"})
        file_contents: dict[str, str] = {}
        load_tasks = [_load_file(f, self.repo_root) for f in relevant_files]
        loaded = await asyncio.gather(*load_tasks, return_exceptions=True)
        for path, content in zip(relevant_files, loaded):
            if isinstance(content, str):
                file_contents[path] = content

        # ── Step 3: Planner ───────────────────────────────────────────────────
        yield _emit("status", {"message": "Planning steps...", "phase": "planner"})
        planner = PlannerAgent()
        plan_result = await planner.run({
            "task": task,
            "files": relevant_files,
            "file_contents": file_contents,
            "history": compressed_history,
            # Feed spec into planner so it plans towards acceptance criteria
            "spec": spec_text,
            "constraints": spec_constraints,
        })
        yield _emit("agent_result", plan_result.to_dict())

        steps: list[dict[str, Any]] = plan_result.data.get("steps", [])
        if not steps:
            yield _emit("error", {"message": "Planner returned no steps."})
            return

        yield _emit("plan", {"steps": steps, "summary": plan_result.data.get("summary", "")})

        # ── Step 4: Execute steps (parallel where possible) ───────────────────
        completed_ids: set[str] = set()
        remaining = list(steps)

        iteration = 0
        max_iterations = len(steps) + 5  # guard against infinite loop

        while remaining and iteration < max_iterations:
            iteration += 1

            # Find steps whose dependencies are all satisfied
            ready = [
                s for s in remaining
                if all(dep in completed_ids for dep in s.get("depends_on", []))
            ]
            if not ready:
                yield _emit("error", {"message": "Dependency cycle or unresolvable steps.", "remaining": [s["id"] for s in remaining]})
                break

            # Group parallel vs sequential within ready batch
            parallel_batch  = [s for s in ready if s.get("parallel", False)]
            sequential_batch = [s for s in ready if not s.get("parallel", False)]

            # Run parallel batch first
            if parallel_batch:
                yield _emit("status", {
                    "message": f"Running {len(parallel_batch)} steps in parallel...",
                    "phase": "parallel",
                    "step_ids": [s["id"] for s in parallel_batch],
                })
                tasks = [
                    self._execute_step_with_retry(s, task, file_contents, compressed_history, all_edits)
                    for s in parallel_batch
                ]
                results = await asyncio.gather(*tasks, return_exceptions=True)
                for step, result in zip(parallel_batch, results):
                    if isinstance(result, Exception):
                        yield _emit("step_error", {"step_id": step["id"], "error": str(result)})
                    else:
                        step_results[step["id"]] = result
                        yield _emit("agent_result", result.to_dict())
                        if result.success and result.data.get("edits"):
                            all_edits.extend(result.data["edits"])
                    completed_ids.add(step["id"])

            # Run sequential batch one by one
            for step in sequential_batch:
                yield _emit("status", {
                    "message": f"Running step: {step['description'][:60]}",
                    "phase": "sequential",
                    "step_id": step["id"],
                })
                try:
                    result = await self._execute_step_with_retry(
                        step, task, file_contents, compressed_history, all_edits
                    )
                    step_results[step["id"]] = result
                    yield _emit("agent_result", result.to_dict())
                    if result.success and result.data.get("edits"):
                        all_edits.extend(result.data["edits"])
                        # Update file_contents with edits for subsequent steps
                        for edit in result.data["edits"]:
                            if edit.get("mode", "replace") == "replace":
                                file_contents[edit["path"]] = edit["content"]
                except Exception as exc:
                    yield _emit("step_error", {"step_id": step["id"], "error": str(exc)})
                completed_ids.add(step["id"])

            remaining = [s for s in remaining if s["id"] not in completed_ids]

        # ── Step 5: Review all edits ──────────────────────────────────────────
        if all_edits:
            yield _emit("status", {"message": "Reviewing all edits...", "phase": "review"})
            reviewer = ReviewerAgent()
            original = {
                e["path"]: file_contents.get(e["path"], "")
                for e in all_edits
            }
            review_result = await reviewer.run({
                "task": task,
                "edits": all_edits,
                "original": original,
                "step": {"description": "Final review of all edits"},
            })
            yield _emit("agent_result", review_result.to_dict())
            yield _emit("review", review_result.data)

        # ── Done ──────────────────────────────────────────────────────────────
        yield _emit("done", {
            "total_steps": len(steps),
            "completed":   len(completed_ids),
            "total_edits": len(all_edits),
            "files_modified": list({e["path"] for e in all_edits}),
        })

    async def _execute_step_with_retry(
        self,
        step: dict[str, Any],
        task: str,
        file_contents: dict[str, str],
        history: list[dict[str, str]],
        accumulated_edits: list[dict[str, Any]],
    ):
        """Wrapper: retry _execute_step up to _STEP_MAX_RETRIES on failure."""
        delay = _RETRY_DELAY_S
        last_exc: Exception | None = None
        for attempt in range(1, _STEP_MAX_RETRIES + 1):
            try:
                result = await self._execute_step(
                    step, task, file_contents, history, accumulated_edits
                )
                if result.success:
                    return result
                # Treat agent-level failures as retryable
                last_exc = RuntimeError(result.error or "agent returned success=False")
            except Exception as exc:
                last_exc = exc

            if attempt < _STEP_MAX_RETRIES:
                logger.warning(
                    "step_retry",
                    step_id=step["id"],
                    attempt=attempt,
                    max=_STEP_MAX_RETRIES,
                    error=str(last_exc),
                )
                await asyncio.sleep(delay)
                delay *= 2  # exponential backoff

        # All retries exhausted — re-raise so caller emits step_error
        raise last_exc or RuntimeError(f"Step {step['id']} failed after {_STEP_MAX_RETRIES} attempts")

    async def _execute_step(
        self,
        step: dict[str, Any],
        task: str,
        file_contents: dict[str, str],
        history: list[dict[str, str]],
        accumulated_edits: list[dict[str, Any]],
    ):
        """Dispatch a single step to the appropriate agent."""
        agent_name = step.get("agent", "editor")
        AgentClass = _AGENT_MAP.get(agent_name, EditorAgent)
        agent = AgentClass()

        step_context = step.get("context", {})

        if agent_name == "editor":
            ctx = {
                "task": task,
                "step": step,
                "file_contents": file_contents,
                "history": history,
                **step_context,
            }
        elif agent_name == "terminal":
            # command might be in step context or description
            cmd = step_context.get("command", step.get("description", ""))
            lang = step_context.get("language", "shell")
            ctx = {
                "command": cmd,
                "language": lang,
                "step": step,
                "cwd": self.repo_root,
                **step_context,
            }
        elif agent_name == "reviewer":
            ctx = {
                "task": task,
                "edits": accumulated_edits,
                "original": file_contents,
                "step": step,
                **step_context,
            }
        elif agent_name == "file_picker":
            # Build current file tree from file_contents keys
            ctx = {
                "task": step.get("description", task),
                "file_tree": "\n".join(file_contents.keys()),
                **step_context,
            }
        else:
            ctx = {"task": task, "step": step, **step_context}

        return await agent.run(ctx)
