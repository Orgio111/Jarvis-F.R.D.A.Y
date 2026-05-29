"""TerminalAgent — executes shell/Python commands via Jarvis sandbox.

Wraps the existing `app/routers/execution.py` sandbox functions.
Does NOT rewrite the sandbox — just calls the internal helpers.

Input context keys:
  command     (str)   — shell command or python code to run
  language    (str)   — "shell" | "python" (default: "shell")
  step        (dict)  — planner step (for logging)
  cwd         (str)   — optional working directory

Output AgentResult.data:
  stdout      (str)
  stderr      (str)
  exit_code   (int)
  interpreted (str)   — LLM interpretation of the output
"""
from __future__ import annotations

import asyncio
from typing import Any

from app.agents.base_agent import AgentResult, BaseAgent
from app.agents.free_model_pool import AgentRole
from app.core.logging import get_logger

logger = get_logger(__name__)


async def _run_in_sandbox(
    command: str,
    language: str,
    cwd: str | None,
) -> tuple[str, str, int]:
    """Delegate to execution.py sandbox helpers.

    Returns (stdout, stderr, exit_code).
    """
    try:
        # Import the internal sandbox helpers
        from app.routers.execution import _run_shell, _run_python  # type: ignore
    except ImportError:
        # Fallback — direct subprocess
        import asyncio.subprocess as sp
        proc = await asyncio.create_subprocess_shell(
            command,
            stdout=sp.PIPE,
            stderr=sp.PIPE,
            cwd=cwd,
        )
        stdout_b, stderr_b = await asyncio.wait_for(proc.communicate(), timeout=60.0)
        return stdout_b.decode(), stderr_b.decode(), proc.returncode or 0

    if language == "python":
        result = await _run_python(code=command, timeout=60)
    else:
        result = await _run_shell(command=command, cwd=cwd, timeout=60)

    stdout   = getattr(result, "stdout",   "") or ""
    stderr   = getattr(result, "stderr",   "") or ""
    exit_code = getattr(result, "exit_code", 0) or 0
    return str(stdout), str(stderr), int(exit_code)


class TerminalAgent(BaseAgent):
    role = AgentRole.TERMINAL

    async def _execute(self, context: dict[str, Any]) -> AgentResult:
        command  = context.get("command", "")
        language = context.get("language", "shell")
        step     = context.get("step", {})
        cwd      = context.get("cwd", None)

        if not command:
            return AgentResult(
                role=self.role, success=False,
                content="", error="'command' is required",
            )

        logger.info(
            "terminal_agent_exec",
            language=language,
            step_id=step.get("id", "?"),
            command=command[:120],
        )

        try:
            stdout, stderr, exit_code = await _run_in_sandbox(command, language, cwd)
        except Exception as exc:
            return AgentResult(
                role=self.role, success=False,
                content="", error=str(exc),
            )

        output_text = (stdout + "\n" + stderr).strip()[:3000]

        # Interpret output with LLM
        messages = [
            {
                "role": "system",
                "content": (
                    "You are a terminal output interpreter. "
                    "Given a command, its output, and exit code, "
                    "briefly explain what happened (1-3 sentences). "
                    "If there was an error, identify the root cause. "
                    "Be direct and technical."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Command: {command}\n"
                    f"Exit code: {exit_code}\n"
                    f"Output:\n{output_text}"
                ),
            },
        ]

        try:
            interpreted, model = await self._chat(
                messages, temperature=0.1, max_tokens=256,
            )
        except Exception as exc:
            interpreted = f"(interpretation failed: {exc})"
            model = ""

        success = exit_code == 0

        return AgentResult(
            role=self.role,
            success=success,
            content=interpreted,
            data={
                "stdout":      stdout[:2000],
                "stderr":      stderr[:1000],
                "exit_code":   exit_code,
                "interpreted": interpreted,
                "command":     command,
            },
            model_used=model,
        )
