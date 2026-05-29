"""ReviewerAgent — reviews proposed edits for correctness, bugs, and style.

Input context keys:
  task        (str)        — original task
  edits       (list[Edit]) — from EditorAgent
  original    (dict)       — {path: original_content} before edits
  step        (dict)       — planner step for context

Output AgentResult.data:
  approved    (bool)
  issues      (list[str])  — each is a short description of a problem
  suggestions (list[str])  — non-blocking improvements
  score       (int)        — 1-10 quality score
"""
from __future__ import annotations

from typing import Any

from app.agents.base_agent import AgentResult, BaseAgent
from app.agents.free_model_pool import AgentRole

_REVIEW_SCHEMA = """{
  "approved": true,
  "score": 8,
  "issues": [],
  "suggestions": ["consider adding a docstring to foo()"]
}"""


class ReviewerAgent(BaseAgent):
    role = AgentRole.REVIEWER

    async def _execute(self, context: dict[str, Any]) -> AgentResult:
        task     = context.get("task", "")
        edits    = context.get("edits", [])
        original = context.get("original", {})
        step     = context.get("step", {})

        if not edits:
            return AgentResult(
                role=self.role,
                success=True,
                content="No edits to review",
                data={"approved": True, "issues": [], "suggestions": [], "score": 10},
            )

        # Build review payload
        edit_blocks = ""
        for edit in edits[:5]:
            path      = edit.get("path", "?")
            new_code  = edit.get("content", "")[:2000]
            orig_code = original.get(path, "")[:1000]
            edit_blocks += (
                f"\n=== {path} ===\n"
                f"ORIGINAL (first 1000 chars):\n{orig_code or '(new file)'}\n\n"
                f"NEW CONTENT (first 2000 chars):\n{new_code}\n"
            )

        messages = [
            {
                "role": "system",
                "content": (
                    "You are a senior code reviewer. "
                    "Review the proposed code changes for: correctness, bugs, security issues, "
                    "performance problems, and adherence to the task. "
                    "Be concise. Approve if there are no blocking issues. "
                    "Output ONLY valid JSON matching this schema:\n"
                    + _REVIEW_SCHEMA
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Task: {task}\n"
                    f"Step: {step.get('description', '')}\n"
                    f"\nCode changes:{edit_blocks}"
                ),
            },
        ]

        content, model = await self._chat(messages, temperature=0.1, max_tokens=1024)

        try:
            parsed      = self._extract_json(content)
            approved    = bool(parsed.get("approved", False))
            issues      = parsed.get("issues", [])
            suggestions = parsed.get("suggestions", [])
            score       = int(parsed.get("score", 5))
        except (ValueError, TypeError):
            approved    = False
            issues      = [content[:500]]
            suggestions = []
            score       = 5

        return AgentResult(
            role=self.role,
            success=True,
            content="Approved" if approved else f"Issues: {'; '.join(issues[:3])}",
            data={
                "approved": approved,
                "issues": issues,
                "suggestions": suggestions,
                "score": score,
            },
            model_used=model,
        )
