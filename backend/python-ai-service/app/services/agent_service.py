"""
Agent Orchestrator  —  Plan → Act → Reflect → Improve
───────────────────────────────────────────────────────
Implements the full agentic loop for complex multi-step tasks.

Loop:
  1. PLAN    – LLM decomposes the goal into ordered steps
  2. ACT     – execute each step (tool call, skill call, or direct LLM)
  3. REFLECT – LLM evaluates whether the goal was met; suggests corrections
  4. IMPROVE – if not satisfied, re-plan with new information (up to max_iterations)

After a successful run the orchestrator checks if a reusable skill should
be created from the sequence of actions taken.

Streaming:
  The loop yields SSE-compatible JSON events so the caller can stream
  progress to the client in real-time.
"""
from __future__ import annotations

import asyncio
import json
import sys
import time
from collections.abc import AsyncGenerator
from typing import Any
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.services import skill_service

logger = get_logger(__name__)

_MAX_ITERATIONS = 5
_MAX_STEPS_PER_PLAN = 10


# ─── Public entry point ───────────────────────────────────────────────────────

async def run_task(
    db: AsyncSession,
    goal: str,
    context: str = "",
    available_skills: list[dict] | None = None,
    user_id: str = "default",
    max_iterations: int = _MAX_ITERATIONS,
) -> AsyncGenerator[dict[str, Any], None]:
    """
    Execute a goal using the plan→act→reflect loop.
    Yields event dicts; caller should serialise to SSE.
    """
    run_id = f"run_{uuid4().hex[:8]}"
    start = time.perf_counter()

    yield _event("AGENT_START", {"runId": run_id, "goal": goal[:200]})

    all_actions: list[dict] = []
    final_answer: str = ""
    satisfied = False

    for iteration in range(1, max_iterations + 1):
        yield _event("AGENT_PLANNING", {"runId": run_id, "iteration": iteration})

        # ── PLAN ──────────────────────────────────────────────────────────────
        try:
            plan = await _plan(goal, context, all_actions, available_skills or [])
        except Exception as exc:
            yield _event("AGENT_ERROR", {"runId": run_id, "phase": "plan", "error": str(exc)})
            break

        yield _event("AGENT_PLAN_READY", {
            "runId": run_id,
            "iteration": iteration,
            "steps": plan["steps"],
        })

        # ── ACT ───────────────────────────────────────────────────────────────
        step_results: list[dict] = []
        for step_idx, step in enumerate(plan["steps"][:_MAX_STEPS_PER_PLAN]):
            yield _event("AGENT_STEP_START", {
                "runId": run_id,
                "stepIndex": step_idx,
                "step": step,
            })
            try:
                result = await _act(db, step, available_skills or [])
            except Exception as exc:
                result = {"error": str(exc), "success": False}

            step_results.append({"step": step, "result": result})
            all_actions.append({"step": step, "result": result})

            yield _event("AGENT_STEP_DONE", {
                "runId": run_id,
                "stepIndex": step_idx,
                "result": result,
            })

        # ── REFLECT ───────────────────────────────────────────────────────────
        yield _event("AGENT_REFLECTING", {"runId": run_id, "iteration": iteration})
        try:
            reflection = await _reflect(goal, step_results)
        except Exception as exc:
            reflection = {"satisfied": False, "answer": "", "feedback": str(exc)}

        final_answer = reflection.get("answer", "")
        satisfied = reflection.get("satisfied", False)

        yield _event("AGENT_REFLECTION", {
            "runId": run_id,
            "iteration": iteration,
            "satisfied": satisfied,
            "answer": final_answer[:500],
            "feedback": reflection.get("feedback", ""),
        })

        if satisfied:
            break

        # Enrich context with feedback for next iteration
        context = (context + "\n\nFeedback: " + reflection.get("feedback", ""))[-2000:]

    elapsed = round((time.perf_counter() - start) * 1000, 1)

    # ── POST-LOOP: auto-skill creation ────────────────────────────────────────
    if satisfied and len(all_actions) >= 2:
        asyncio.ensure_future(
            _maybe_create_skill(db, goal, all_actions, final_answer)
        )

    yield _event("AGENT_DONE", {
        "runId": run_id,
        "satisfied": satisfied,
        "finalAnswer": final_answer,
        "totalActions": len(all_actions),
        "iterations": iteration,
        "elapsedMs": elapsed,
    })


# ─── Phase implementations ────────────────────────────────────────────────────

async def _plan(
    goal: str,
    context: str,
    prior_actions: list[dict],
    skills: list[dict],
) -> dict[str, Any]:
    from app.providers.router import ProviderRouter

    pr = ProviderRouter.get()
    provider = pr.get_active_provider()
    if provider is None:
        # Fallback: single-step plan
        return {"steps": [{"type": "llm", "instruction": goal}]}

    skill_names = [s["name"] for s in skills[:10]]
    prior_summary = _summarise_actions(prior_actions)

    system = (
        "You are a task planner. Break the goal into ≤8 concrete, sequential steps. "
        "Output ONLY a JSON object: {\"steps\": [{\"type\": \"llm\"|\"skill\"|\"code\", "
        "\"instruction\": \"…\", \"skill_id\": \"…\" (optional), \"code\": \"…\" (optional)}]}. "
        "Use type='skill' only if the skill name exactly matches an available skill. "
        "Use type='code' only for simple calculations. Default to type='llm'. "
        "No markdown, no explanation — JSON only."
    )
    user = (
        f"Goal: {goal}\n"
        f"Context: {context[:400]}\n"
        f"Available skills: {', '.join(skill_names) or 'none'}\n"
        f"Prior actions: {prior_summary}\n\n"
        "Output the plan:"
    )
    result = await provider.chat(
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        model_id="",
        max_tokens=512,
    )
    raw = result.get("choices", [{}])[0].get("message", {}).get("content", "")
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1].lstrip("json").strip()
    plan = json.loads(raw)
    return plan


async def _act(
    db: AsyncSession,
    step: dict[str, Any],
    skills: list[dict],
) -> dict[str, Any]:
    step_type = step.get("type", "llm")
    instruction = step.get("instruction", "")

    if step_type == "skill":
        skill_id = step.get("skill_id", "")
        if skill_id:
            params = step.get("params", {})
            return await skill_service.execute(db, skill_id, params)
        # Fall through to LLM if no skill_id
        step_type = "llm"

    if step_type == "code":
        code = step.get("code", "")
        if code:
            return await _run_code_sandboxed(code)

    # Default: LLM reasoning step
    return await _llm_step(instruction)


async def _run_code_sandboxed(code: str, timeout_s: int = 10) -> dict[str, Any]:
    """
    Execute a short code snippet in a child subprocess instead of the live
    interpreter.  This prevents the agent from mutating process state or
    accessing secrets available in the parent environment.
    """
    try:
        proc = await asyncio.create_subprocess_exec(
            sys.executable, "-c", code,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout_bytes, stderr_bytes = await asyncio.wait_for(
                proc.communicate(), timeout=timeout_s
            )
        except asyncio.TimeoutError:
            proc.kill()
            await proc.communicate()
            return {"success": False, "error": f"Code execution timed out after {timeout_s}s"}

        stdout = stdout_bytes.decode(errors="replace").strip()
        stderr = stderr_bytes.decode(errors="replace").strip()
        if proc.returncode != 0:
            return {"success": False, "error": stderr or f"exit code {proc.returncode}"}
        return {"success": True, "output": stdout}
    except Exception as exc:
        return {"success": False, "error": str(exc)}


async def _llm_step(instruction: str) -> dict[str, Any]:
    from app.providers.router import ProviderRouter

    pr = ProviderRouter.get()
    provider = pr.get_active_provider()
    if provider is None:
        return {"success": False, "error": "No provider available"}

    result = await provider.chat(
        messages=[{"role": "user", "content": instruction}],
        model_id="",
        max_tokens=1024,
    )
    content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
    return {"success": True, "output": content}


async def _reflect(goal: str, step_results: list[dict]) -> dict[str, Any]:
    from app.providers.router import ProviderRouter

    pr = ProviderRouter.get()
    provider = pr.get_active_provider()
    if provider is None:
        # Simple heuristic: consider satisfied if no errors
        errors = [r for r in step_results if not r.get("result", {}).get("success", True)]
        return {
            "satisfied": len(errors) == 0,
            "answer": str(step_results[-1].get("result", {}).get("output", "")),
            "feedback": "Provider unavailable — heuristic evaluation used",
        }

    summary = json.dumps([
        {"step": s["step"].get("instruction", ""), "output": str(s["result"])[:200]}
        for s in step_results
    ], indent=None)

    system = (
        "You are a quality evaluator. Given a goal and the results of execution steps, "
        "decide if the goal was fully satisfied. "
        "Output ONLY JSON: {\"satisfied\": true|false, \"answer\": \"…\", \"feedback\": \"…\"}. "
        "`answer` is the final answer to the user (empty string if not satisfied). "
        "`feedback` explains what is missing or what to try next. No markdown."
    )
    user = (
        f"Goal: {goal}\n"
        f"Steps executed:\n{summary[:1200]}\n\n"
        "Evaluate:"
    )
    result = await provider.chat(
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        model_id="",
        max_tokens=512,
    )
    raw = result.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1].lstrip("json").strip()
    return json.loads(raw)


async def _maybe_create_skill(
    db: AsyncSession,
    goal: str,
    actions: list[dict],
    final_answer: str,
) -> None:
    """Heuristically decide if the task warrants a reusable skill."""
    if len(actions) < 2:
        return

    # Only create if there are meaningful llm steps (not trivial single-answer)
    llm_steps = [a for a in actions if a["step"].get("type") == "llm"]
    if len(llm_steps) < 2:
        return

    try:
        task_context = (
            f"Goal: {goal}\n"
            f"Actions taken: {json.dumps([a['step'] for a in actions], indent=None)[:600]}\n"
            f"Result: {final_answer[:300]}"
        )
        await skill_service.generate_and_store(
            db=db,
            name=f"Auto: {goal[:50]}",
            description=f"Auto-generated skill from task: {goal[:200]}",
            task_context=task_context,
            category="auto",
            origin="generated",
        )
        logger.info("auto_skill_created", goal=goal[:60])
    except Exception as exc:
        logger.debug("auto_skill_skipped", reason=str(exc))


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _summarise_actions(actions: list[dict]) -> str:
    if not actions:
        return "none"
    return "; ".join(
        f"{a['step'].get('instruction', '')[:60]} → {str(a['result'])[:60]}"
        for a in actions[-4:]
    )


def _event(event_type: str, data: dict[str, Any]) -> dict[str, Any]:
    return {"event": event_type, "ts": round(time.time(), 3), **data}
