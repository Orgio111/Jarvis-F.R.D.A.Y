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

Swarm helper:
  score_edits(task, step, edits, original) → int  (1-10)
  Used by Orchestrator swarm mode to pick the better of two EditorAgent outputs.
"""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from app.agents.base_agent import AgentResult, BaseAgent
from app.agents.free_model_pool import AgentRole

_REVIEW_SCHEMA = """{
  "approved": true,
  "score": 8,
  "issues": [],
  "suggestions": ["consider adding a docstring to foo()"]
}"""


class _ReviewerOutput(BaseModel):
    approved: bool
    score: int
    issues: list[str] = []
    suggestions: list[str] = []


class ReviewerAgent(BaseAgent):
    role = AgentRole.REVIEWER
    output_schema = _ReviewerOutput

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

    async def score_edits(
        self,
        task: str,
        step: dict,
        edits: list[dict],
        original: dict[str, str],
    ) -> int:
        """Score a set of edits 1-10. Used by swarm mode to pick the winner.

        Lighter-weight than full _execute — just requests a score integer.
        """
        if not edits:
            return 0

        edit_blocks = ""
        for edit in edits[:4]:
            path     = edit.get("path", "?")
            new_code = edit.get("content", "")[:1500]
            orig     = original.get(path, "")[:600]
            edit_blocks += (
                f"\n=== {path} ===\n"
                f"ORIGINAL:\n{orig or '(new file)'}\n\nNEW:\n{new_code}\n"
            )

        messages = [
            {
                "role": "system",
                "content": (
                    "You are a senior code reviewer. "
                    "Score the following code changes 1-10 based on: "
                    "correctness, clarity, minimal diff (no unnecessary changes), "
                    "and how well it satisfies the task. "
                    "Reply with ONLY a single integer 1-10. No explanation."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Task: {task}\nStep: {step.get('description', '')}"
                    f"\n\nChanges:{edit_blocks}"
                ),
            },
        ]

        try:
            content, _ = await self._chat(messages, temperature=0.05, max_tokens=8)
            return max(1, min(10, int(content.strip().split()[0])))
        except Exception:
            return 5  # neutral score on error
