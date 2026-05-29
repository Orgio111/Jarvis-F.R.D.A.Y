"""FilePickerAgent — identifies which files in a codebase are relevant to a task.

Input context keys:
  task       (str)  — user's task description
  file_tree  (str)  — newline-separated list of repo paths (from `find` or git ls-files)
  max_files  (int)  — optional, default 10

Output AgentResult.data:
  files      (list[str])  — relative paths most relevant to the task
  reasoning  (str)        — brief explanation
"""
from __future__ import annotations

from typing import Any

from app.agents.base_agent import AgentResult, BaseAgent
from app.agents.free_model_pool import AgentRole


class FilePickerAgent(BaseAgent):
    role = AgentRole.FILE_PICKER

    async def _execute(self, context: dict[str, Any]) -> AgentResult:
        task      = context.get("task", "")
        file_tree = context.get("file_tree", "")
        max_files = int(context.get("max_files", 10))

        if not task:
            return AgentResult(
                role=self.role, success=False,
                content="", error="'task' is required in context",
            )

        # Truncate file tree if huge (model ctx limit)
        tree_lines = file_tree.strip().splitlines()
        if len(tree_lines) > 500:
            tree_lines = tree_lines[:500]
            file_tree = "\n".join(tree_lines) + "\n... (truncated)"

        messages = [
            {
                "role": "system",
                "content": (
                    "You are a senior engineer analyzing a codebase. "
                    "Given a task description and a file tree, identify the "
                    f"top {max_files} files most relevant to completing the task. "
                    "Respond ONLY with valid JSON in this exact shape:\n"
                    '{"files": ["path/a.py", "path/b.ts"], "reasoning": "..."}\n'
                    "No markdown, no explanation outside the JSON."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Task: {task}\n\n"
                    f"File tree:\n{file_tree}"
                ),
            },
        ]

        content, model = await self._chat(messages, temperature=0.1, max_tokens=1024)

        try:
            parsed = self._extract_json(content)
            files     = parsed.get("files", [])
            reasoning = parsed.get("reasoning", "")
        except ValueError:
            # best-effort: split lines that look like paths
            files     = [l.strip() for l in content.splitlines() if "/" in l or "." in l][:max_files]
            reasoning = content

        return AgentResult(
            role=self.role,
            success=True,
            content=reasoning,
            data={"files": files[:max_files], "reasoning": reasoning},
            model_used=model,
        )
