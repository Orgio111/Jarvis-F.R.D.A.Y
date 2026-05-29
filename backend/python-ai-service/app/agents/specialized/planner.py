"""PlannerAgent — decomposes a task into ordered, dependency-aware steps.

Input context keys:
  task       (str)         — user's task description
  files      (list[str])   — relevant files (from FilePickerAgent)
  file_contents (dict)     — optional {path: content} for context
  history    (list[dict])  — optional compressed conversation history

Output AgentResult.data:
  steps      (list[Step])  — ordered plan
  summary    (str)         — one-line task summary

Step shape:
  {
    "id":          "step_1",
    "description": "...",
    "agent":       "editor" | "terminal" | "reviewer" | "file_picker",
    "depends_on":  [],          # list of step ids this step waits for
    "parallel":    true/false,  # can run alongside sibling steps?
    "input_files": ["..."],
    "context":     {}           # extra kv passed to the assigned agent
  }
"""
from __future__ import annotations

from typing import Any

from app.agents.base_agent import AgentResult, BaseAgent
from app.agents.free_model_pool import AgentRole


_STEP_SCHEMA = """{
  "summary": "one-line task summary",
  "steps": [
    {
      "id": "step_1",
      "description": "...",
      "agent": "editor",
      "depends_on": [],
      "parallel": false,
      "input_files": ["src/main.py"],
      "context": {}
    }
  ]
}"""


class PlannerAgent(BaseAgent):
    role = AgentRole.PLANNER

    async def _execute(self, context: dict[str, Any]) -> AgentResult:
        task          = context.get("task", "")
        files         = context.get("files", [])
        file_contents = context.get("file_contents", {})
        history       = context.get("history", [])

        if not task:
            return AgentResult(
                role=self.role, success=False,
                content="", error="'task' is required",
            )

        # Build file context block (truncated)
        file_ctx = ""
        for path in files[:8]:
            content_snippet = file_contents.get(path, "")[:800]
            if content_snippet:
                file_ctx += f"\n--- {path} ---\n{content_snippet}\n"

        history_ctx = ""
        if history:
            for m in history[-4:]:
                history_ctx += f"[{m.get('role','')}]: {m.get('content','')[:300]}\n"

        messages = [
            {
                "role": "system",
                "content": (
                    "You are an expert software engineering planner. "
                    "Break down the given task into a minimal, ordered list of steps. "
                    "Mark steps that can run in parallel (parallel=true) when they have no dependency between them. "
                    "Assign the correct agent to each step: "
                    "'editor' for code changes, 'terminal' for shell/test commands, "
                    "'reviewer' for code review, 'file_picker' to find more files. "
                    "Output ONLY valid JSON matching this exact schema — no markdown:\n"
                    + _STEP_SCHEMA
                ),
            },
        ]

        if history_ctx:
            messages.append({"role": "user", "content": f"Conversation history:\n{history_ctx}"})

        user_content = f"Task: {task}\n\nRelevant files: {', '.join(files) or 'none'}"
        if file_ctx:
            user_content += f"\n\nFile snippets:{file_ctx}"
        messages.append({"role": "user", "content": user_content})

        content, model = await self._chat(messages, temperature=0.15, max_tokens=2048)

        try:
            parsed  = self._extract_json(content)
            steps   = parsed.get("steps", [])
            summary = parsed.get("summary", task[:80])
        except ValueError:
            steps   = []
            summary = task[:80]

        # Ensure each step has required keys
        for i, step in enumerate(steps):
            step.setdefault("id", f"step_{i+1}")
            step.setdefault("depends_on", [])
            step.setdefault("parallel", False)
            step.setdefault("input_files", [])
            step.setdefault("context", {})
            step.setdefault("agent", "editor")

        return AgentResult(
            role=self.role,
            success=True,
            content=summary,
            data={"steps": steps, "summary": summary},
            model_used=model,
        )
