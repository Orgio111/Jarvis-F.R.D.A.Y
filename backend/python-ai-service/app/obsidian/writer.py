"""
ObsidianWriter — low-level Obsidian vault file operations.

Vault structure:
  {vault_root}/
  ├── swarm/
  │   ├── agents.md          — live agent registry
  │   ├── decisions.md       — agent decision log
  │   └── {agent_id}/        — per-agent diary folder
  │       └── YYYY-MM-DD.md
  ├── memory/
  │   ├── short_term.md      — recent turns (last 50)
  │   ├── long_term.md       — crystallised facts
  │   └── search_index.md    — auto-generated backlink index
  ├── tasks/
  │   └── YYYY-MM-DD.md      — task execution log
  ├── self_improvement/
  │   ├── prompt_wins.md     — prompts that worked
  │   └── prompt_failures.md — prompts that failed
  └── _index.md              — vault root index (auto-updated)
"""
from __future__ import annotations

import os
import re
import asyncio
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_FRONTMATTER_RE = re.compile(r"^---\n.*?\n---\n", re.DOTALL)


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _wikilink(target: str, alias: str | None = None) -> str:
    if alias:
        return f"[[{target}|{alias}]]"
    return f"[[{target}]]"


def _tags_line(tags: list[str]) -> str:
    return "tags: [" + ", ".join(tags) + "]"


class ObsidianWriter:
    """
    Thread-safe Obsidian vault writer.
    All write operations are serialised through asyncio.Lock to prevent
    concurrent file corruption.
    """

    def __init__(self, vault_root: str):
        self.vault = Path(vault_root)
        self._lock = asyncio.Lock()
        self._ensure_structure()

    # ── Vault structure ───────────────────────────────────────────────────────

    def _ensure_structure(self):
        dirs = [
            "swarm",
            "memory",
            "tasks",
            "self_improvement",
            "agents",
        ]
        for d in dirs:
            (self.vault / d).mkdir(parents=True, exist_ok=True)

        # Root index
        index = self.vault / "_index.md"
        if not index.exists():
            index.write_text(
                "---\n"
                "title: Jarvis Knowledge Graph\n"
                f"created: {_now_iso()}\n"
                "tags: [index, jarvis]\n"
                "---\n\n"
                "# 🧠 Jarvis Memory Brain\n\n"
                "## Sections\n"
                "- [[swarm/agents]] — Agent registry\n"
                "- [[swarm/decisions]] — Decision log\n"
                "- [[memory/short_term]] — Recent memory\n"
                "- [[memory/long_term]] — Long-term facts\n"
                "- [[tasks/index]] — Task history\n"
                "- [[self_improvement/prompt_wins]] — What worked\n"
                "- [[self_improvement/prompt_failures]] — What failed\n",
                encoding="utf-8",
            )

    # ── Core write primitives ─────────────────────────────────────────────────

    async def append(self, rel_path: str, content: str):
        """Append content to a vault file. Creates file with frontmatter if missing."""
        async with self._lock:
            path = self.vault / rel_path
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, "a", encoding="utf-8") as f:
                f.write(content)

    async def overwrite(self, rel_path: str, content: str):
        """Overwrite entire file."""
        async with self._lock:
            path = self.vault / rel_path
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")

    async def prepend_frontmatter(self, rel_path: str, frontmatter: dict[str, Any]):
        """Add/update YAML frontmatter block."""
        async with self._lock:
            path = self.vault / rel_path
            path.parent.mkdir(parents=True, exist_ok=True)

            existing = path.read_text(encoding="utf-8") if path.exists() else ""
            existing = _FRONTMATTER_RE.sub("", existing)

            fm_lines = ["---"]
            for k, v in frontmatter.items():
                if isinstance(v, list):
                    fm_lines.append(f"{k}: [{', '.join(str(i) for i in v)}]")
                else:
                    fm_lines.append(f"{k}: {v}")
            fm_lines.append("---\n")

            path.write_text("\n".join(fm_lines) + existing, encoding="utf-8")

    # ── High-level helpers ────────────────────────────────────────────────────

    async def log_entry(
        self,
        rel_path: str,
        body: str,
        heading: str | None = None,
        tags: list[str] | None = None,
    ):
        """
        Append a timestamped log entry to a file.
        Initialises the file with frontmatter on first write.
        """
        path = self.vault / rel_path
        if not path.exists():
            title = rel_path.replace("/", " / ").replace(".md", "").title()
            header = (
                f"---\n"
                f"title: {title}\n"
                f"created: {_now_iso()}\n"
                f"{_tags_line(tags or [])}\n"
                f"---\n\n"
                f"# {title}\n\n"
            )
            await self.append(rel_path, header)

        ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        block = f"\n## {heading or ts}\n\n{body}\n"
        await self.append(rel_path, block)

    async def upsert_section(self, rel_path: str, section_id: str, content: str):
        """
        Replace a named section (## section_id) or append if not present.
        Used for updating agent registry entries in-place.
        """
        async with self._lock:
            path = self.vault / rel_path
            path.parent.mkdir(parents=True, exist_ok=True)

            if not path.exists():
                path.write_text(
                    f"---\ntitle: {rel_path}\ncreated: {_now_iso()}\n---\n\n",
                    encoding="utf-8",
                )

            text = path.read_text(encoding="utf-8")
            pattern = re.compile(
                rf"(## {re.escape(section_id)}\n)(.*?)(?=\n## |\Z)", re.DOTALL
            )
            replacement = f"## {section_id}\n{content}\n"
            if pattern.search(text):
                text = pattern.sub(replacement, text)
            else:
                text += f"\n{replacement}"

            path.write_text(text, encoding="utf-8")

    def abs_path(self, rel_path: str) -> Path:
        return self.vault / rel_path
