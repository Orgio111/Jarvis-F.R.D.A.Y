"""FilePickerAgent — identifies which files in a codebase are relevant to a task.

Two-phase approach (graphify / cocoindex-code pattern):
  1. LLM seed phase  — model picks up to (max_files // 2) seed files by name/path
  2. Graph expansion — CodeGraph BFS from seeds pulls in real import dependencies

This hybrid beats pure-LLM picking because:
  - LLM is good at naming relevant entry points from a file tree
  - Graph traversal adds transitive deps the LLM never sees (helper modules, types, etc.)
  - Saves ~30-50% tokens vs asking LLM to reason about all dependencies

Input context keys:
  task       (str)  — user's task description
  file_tree  (str)  — newline-separated list of repo paths (from `find` or git ls-files)
  max_files  (int)  — optional, default 10
  repo_root  (str)  — optional, enables graph expansion (skipped if not provided)

Output AgentResult.data:
  files      (list[str])  — relative paths most relevant to the task
  seeds      (list[str])  — LLM-chosen seed files (subset)
  reasoning  (str)        — brief explanation
  graph_used (bool)       — whether graph expansion ran
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
        repo_root = context.get("repo_root", "")

        if not task:
            return AgentResult(
                role=self.role, success=False,
                content="", error="'task' is required in context",
            )

        # Truncate file tree if huge
        tree_lines = file_tree.strip().splitlines()
        if len(tree_lines) > 500:
            tree_lines = tree_lines[:500]
            file_tree = "\n".join(tree_lines) + "\n... (truncated)"

        # ── Phase 1: LLM picks seed files ─────────────────────────────────────
        seed_budget = max(3, max_files // 2)

        messages = [
            {
                "role": "system",
                "content": (
                    "You are a senior engineer analyzing a codebase. "
                    "Given a task and a file tree, identify the "
                    f"top {seed_budget} ENTRY-POINT files most relevant to the task. "
                    "Focus on files that directly implement the feature or are the main "
                    "entry points — not transitive helpers (those will be found automatically). "
                    "Respond ONLY with valid JSON:\n"
                    '{"files": ["path/a.py", "path/b.ts"], "reasoning": "..."}\n'
                    "No markdown, no explanation outside the JSON."
                ),
            },
            {
                "role": "user",
                "content": f"Task: {task}\n\nFile tree:\n{file_tree}",
            },
        ]

        content, model = await self._chat(messages, temperature=0.1, max_tokens=1024)

        try:
            parsed    = self._extract_json(content)
            seeds     = parsed.get("files", [])[:seed_budget]
            reasoning = parsed.get("reasoning", "")
        except ValueError:
            seeds     = [l.strip() for l in content.splitlines() if "/" in l or "." in l][:seed_budget]
            reasoning = content

        # ── Phase 2: Graph expansion ───────────────────────────────────────────
        graph_used = False
        expanded: list[str] = list(seeds)

        if repo_root and seeds:
            try:
                from app.agents.code_graph import CodeGraph
                import asyncio

                # Build graph in thread pool (sync I/O)
                loop = asyncio.get_event_loop()
                graph = await loop.run_in_executor(None, CodeGraph.build, repo_root)

                # Validate seeds exist in graph (LLM can hallucinate paths)
                valid_seeds = [s for s in seeds if s in graph.all_files()]

                if valid_seeds:
                    # BFS 2 hops from seeds
                    reachable = graph.reachable(valid_seeds, hops=2)
                    # Remove seeds themselves, rank remaining by hub score
                    candidates = list(reachable - set(valid_seeds))
                    ranked = graph.most_connected(candidates, top_n=max_files - len(valid_seeds))
                    expanded = valid_seeds + ranked
                    graph_used = True

            except Exception as exc:
                # Graph expansion is best-effort — never fail the whole pick
                from app.core.logging import get_logger
                get_logger(__name__).warning("graph_expansion_failed", error=str(exc))

        final_files = expanded[:max_files]

        return AgentResult(
            role=self.role,
            success=True,
            content=reasoning,
            data={
                "files":      final_files,
                "seeds":      seeds,
                "reasoning":  reasoning,
                "graph_used": graph_used,
            },
            model_used=model,
        )
