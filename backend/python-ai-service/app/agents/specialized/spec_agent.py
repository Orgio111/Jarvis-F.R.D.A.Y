"""SpecAgent — generates a concise spec/PRD before the planner runs.

Spec-driven development (inspired by spec-kit pattern):
  Writing a spec first reduces planner hallucination by giving it concrete
  acceptance criteria, constraints, and a scope boundary.

Input context keys:
  task       (str)         — user's task description
  files      (list[str])   — relevant files already identified
  file_contents (dict)     — {path: content} snippet map
  history    (list[dict])  — compressed conversation history

Output AgentResult.data:
  spec       (str)         — markdown spec with acceptance criteria
  scope      (list[str])   — which files / components are in scope
  out_of_scope (list[str]) — explicitly excluded concerns
  constraints (list[str])  — hard constraints (don't break X, must use Y)
"""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from app.agents.base_agent import AgentResult, BaseAgent
from app.agents.free_model_pool import AgentRole


class _SpecOutput(BaseModel):
    spec: str
    scope: list[str] = []
    out_of_scope: list[str] = []
    constraints: list[str] = []


class SpecAgent(BaseAgent):
    role = AgentRole.PLANNER  # use planner model — needs reasoning
    output_schema = _SpecOutput

    _SYSTEM = """\
You are a senior software architect. Your job is to write a concise spec \
for a coding task before any code is written.

Output a JSON object with this shape:
{
  "spec": "## Task\\n...\\n## Acceptance Criteria\\n- [ ] ...\\n## Constraints\\n- ...",
  "scope": ["file_or_component_1", "file_or_component_2"],
  "out_of_scope": ["thing_we_wont_touch"],
  "constraints": ["must not break existing tests", "stay within current architecture"]
}

Be specific. The spec should be short (under 400 words). No fluff.
Acceptance criteria must be testable and unambiguous.
"""

    async def _execute(self, context: dict[str, Any]) -> AgentResult:
        task: str = context.get("task", "")
        files: list[str] = context.get("files", [])
        file_contents: dict[str, str] = context.get("file_contents", {})
        history: list[dict] = context.get("history", [])

        # Build file snippet summary (first 300 chars per file)
        file_snippets = "\n".join(
            f"// {p}\n{c[:300]}" for p, c in list(file_contents.items())[:6]
        )

        messages = [
            {"role": "system", "content": self._SYSTEM},
            *history[-4:],   # last 4 turns for context
            {
                "role": "user",
                "content": (
                    f"Task: {task}\n\n"
                    f"Relevant files: {', '.join(files[:10]) or 'none identified yet'}\n\n"
                    f"File snippets:\n{file_snippets or '(none)'}\n\n"
                    "Write the spec now."
                ),
            },
        ]

        content, model_used = await self._chat(
            messages, temperature=0.15, max_tokens=1024
        )

        try:
            parsed = self._extract_json(content)
            spec_text = parsed.get("spec", content)
            scope = parsed.get("scope", files[:5])
            out_of_scope = parsed.get("out_of_scope", [])
            constraints = parsed.get("constraints", [])
        except Exception:
            spec_text = content
            scope = files[:5]
            out_of_scope = []
            constraints = []

        return AgentResult(
            role=self.role,
            success=True,
            content=spec_text,
            model_used=model_used,
            data={
                "spec": spec_text,
                "scope": scope,
                "out_of_scope": out_of_scope,
                "constraints": constraints,
            },
        )
