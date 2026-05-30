"""EditorAgent — generates or modifies code for a given step.

Input context keys:
  task         (str)         — overall task description
  step         (dict)        — planner step dict
  file_contents (dict)       — {path: content} for input_files in step
  history      (list[dict])  — compressed conversation history

Output AgentResult.data:
  edits        (list[Edit])  — list of file edits
  explanation  (str)

Edit shape:
  {
    "path":    "relative/file.py",
    "content": "...full new file content...",
    "mode":    "replace" | "patch"   # patch = unified diff, replace = full file
  }
"""
from __future__ import annotations

from typing import Any

from app.agents.base_agent import AgentResult, BaseAgent
from app.agents.free_model_pool import AgentRole

_EDIT_SCHEMA = """{
  "explanation": "what was done and why",
  "edits": [
    {
      "path": "src/module.py",
      "content": "...full file or unified diff...",
      "mode": "replace"
    }
  ]
}"""


class EditorAgent(BaseAgent):
    role = AgentRole.EDITOR

    async def _execute(self, context: dict[str, Any]) -> AgentResult:
        task          = context.get("task", "")
        step          = context.get("step", {})
        file_contents = context.get("file_contents", {})
        history       = context.get("history", [])

        step_desc    = step.get("description", task)
        input_files  = step.get("input_files", [])
        extra_ctx    = step.get("context", {})

        # Build file blocks (cap at 3000 chars each)
        file_blocks = ""
        for path in input_files[:6]:
            raw = file_contents.get(path, "")
            snippet = raw[:3000] + ("\n... [truncated]" if len(raw) > 3000 else "")
            if snippet:
                file_blocks += f"\n```\n// FILE: {path}\n{snippet}\n```\n"

        history_ctx = ""
        for m in (history or [])[-4:]:
            history_ctx += f"[{m.get('role','')}]: {m.get('content','')[:300]}\n"

        messages = [
            {
                "role": "system",
                "content": (
                    "You are an expert software engineer. "
                    "Implement the described change precisely. "
                    "For each modified or created file, output the FULL new file content (mode=replace). "
                    "Use mode=patch and unified diff format ONLY for very large files (>200 lines). "
                    "Output ONLY valid JSON matching this schema — no markdown fences:\n"
                    + _EDIT_SCHEMA
                ),
            },
        ]

        if history_ctx:
            messages.append({"role": "user", "content": f"Context:\n{history_ctx}"})

        user_msg = f"Overall task: {task}\n\nStep to implement: {step_desc}"
        if extra_ctx:
            user_msg += f"\n\nExtra context: {extra_ctx}"
        if file_blocks:
            user_msg += f"\n\nCurrent file contents:{file_blocks}"
        messages.append({"role": "user", "content": user_msg})

        # Swarm mode can override temperature for diversity between agents
        temperature = context.get("_swarm_temperature", 0.1)

        content, model = await self._chat(
            messages,
            temperature=temperature,
            max_tokens=4096,
        )

        try:
            parsed      = self._extract_json(content)
            edits       = parsed.get("edits", [])
            explanation = parsed.get("explanation", "")
        except ValueError:
            # raw response — treat as single file content if we know the path
            edits = []
            if input_files:
                edits = [{"path": input_files[0], "content": content, "mode": "replace"}]
            explanation = "Raw response (JSON parse failed)"

        # Normalise edits
        for edit in edits:
            edit.setdefault("mode", "replace")

        return AgentResult(
            role=self.role,
            success=True,
            content=explanation,
            data={"edits": edits, "explanation": explanation},
            model_used=model,
        )
