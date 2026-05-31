"""Prompt Library store — in-memory + Redis persistence."""
from __future__ import annotations

import json
import logging
import os
from typing import Any

from .models import PromptTemplate

logger = logging.getLogger(__name__)

_REDIS_TTL = 60 * 60 * 24 * 30  # 30 days

# Builtin starter templates
_BUILTINS: list[dict] = [
    {
        "name": "Code Review",
        "description": "Review code for bugs, style, and improvements",
        "category": "code",
        "tags": ["review", "code"],
        "body": "Review the following {{language}} code:\n\n```{{language}}\n{{code}}\n```\n\nFocus on:\n1. Bugs and logic errors\n2. Performance issues\n3. Code style and readability\n4. Security concerns\n\nProvide actionable feedback.",
    },
    {
        "name": "Research Summary",
        "description": "Summarize a research topic with key findings",
        "category": "research",
        "tags": ["research", "summary"],
        "body": "Research the following topic and provide a comprehensive summary:\n\nTopic: {{topic}}\n\nInclude:\n- Key concepts and definitions\n- Current state of knowledge\n- Main debates or open questions\n- Practical implications\n- Recommended next steps",
    },
    {
        "name": "System Prompt Base",
        "description": "Base system prompt for JARVIS agents",
        "category": "system",
        "tags": ["system", "agent"],
        "body": "You are JARVIS, an autonomous AI operating system.\n\nCapabilities: {{capabilities}}\nCurrent task: {{task}}\nConstraints: {{constraints}}\n\nAlways think step by step. Be precise, efficient, and transparent about your reasoning.",
    },
    {
        "name": "Bug Report Analysis",
        "description": "Analyze a bug report and suggest fixes",
        "category": "code",
        "tags": ["debug", "code"],
        "body": "Analyze the following bug report:\n\nError: {{error}}\nContext: {{context}}\nExpected behavior: {{expected}}\nActual behavior: {{actual}}\n\nProvide:\n1. Root cause analysis\n2. Step-by-step fix\n3. Prevention strategies",
    },
    {
        "name": "Task Decomposition",
        "description": "Break a complex task into subtasks",
        "category": "general",
        "tags": ["planning", "decomposition"],
        "body": "Decompose the following complex task into manageable subtasks:\n\nTask: {{task}}\nGoal: {{goal}}\nConstraints: {{constraints}}\n\nOutput a structured plan with:\n- Ordered subtasks\n- Dependencies\n- Estimated complexity for each\n- Success criteria",
    },
]


class PromptLibraryStore:
    """Singleton store for prompt templates."""

    _instance: "PromptLibraryStore | None" = None

    def __init__(self) -> None:
        self._templates: dict[str, PromptTemplate] = {}
        self._redis = None
        self._try_connect_redis()
        self._seed_builtins()

    @classmethod
    def get(cls) -> "PromptLibraryStore":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    # ── Redis ─────────────────────────────────────────────────────────────────

    def _try_connect_redis(self) -> None:
        try:
            import redis as redis_lib
            url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
            self._redis = redis_lib.from_url(url, decode_responses=True)
            self._redis.ping()
            self._load_from_redis()
            logger.info("PromptLibraryStore: Redis connected")
        except Exception:
            logger.warning("PromptLibraryStore: Redis unavailable — memory only")
            self._redis = None

    def _redis_key(self, template_id: str) -> str:
        return f"jarvis:prompt_lib:{template_id}"

    def _redis_index_key(self) -> str:
        return "jarvis:prompt_lib:_index"

    def _load_from_redis(self) -> None:
        if not self._redis:
            return
        try:
            ids = self._redis.smembers(self._redis_index_key())
            for tid in ids:
                raw = self._redis.get(self._redis_key(tid))
                if raw:
                    tpl = PromptTemplate.from_dict(json.loads(raw))
                    self._templates[tpl.template_id] = tpl
        except Exception as exc:
            logger.warning("Redis load failed: %s", exc)

    # ── Builtins ──────────────────────────────────────────────────────────────

    def _seed_builtins(self) -> None:
        # Only seed if store is empty
        if self._templates:
            return
        for b in _BUILTINS:
            tpl = PromptTemplate(
                name=b["name"],
                description=b["description"],
                category=b["category"],
                tags=b["tags"],
                metadata={"builtin": True},
            )
            tpl.add_version(b["body"], notes="Initial builtin version")
            self._templates[tpl.template_id] = tpl
            self._persist(tpl)

    # ── CRUD ──────────────────────────────────────────────────────────────────

    def create(
        self,
        name: str,
        body: str,
        description: str = "",
        category: str = "general",
        tags: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
        notes: str = "",
    ) -> PromptTemplate:
        tpl = PromptTemplate(
            name=name,
            description=description,
            category=category,
            tags=tags or [],
            metadata=metadata or {},
        )
        tpl.add_version(body, notes=notes)
        self._templates[tpl.template_id] = tpl
        self._persist(tpl)
        return tpl

    def get(self, template_id: str) -> PromptTemplate | None:
        return self._templates.get(template_id)

    def list(
        self,
        category: str | None = None,
        tag: str | None = None,
        search: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict]:
        results = []
        for tpl in self._templates.values():
            if category and tpl.category != category:
                continue
            if tag and tag not in tpl.tags:
                continue
            if search:
                q = search.lower()
                if q not in tpl.name.lower() and q not in tpl.description.lower():
                    continue
            results.append(tpl.to_dict(include_versions=False))
        results.sort(key=lambda x: x["updated_at"], reverse=True)
        return results[offset: offset + limit]

    def add_version(self, template_id: str, body: str, notes: str = "") -> bool:
        tpl = self._templates.get(template_id)
        if not tpl:
            return False
        tpl.add_version(body, notes=notes)
        self._persist(tpl)
        return True

    def update(self, template_id: str, **kwargs: Any) -> bool:
        tpl = self._templates.get(template_id)
        if not tpl:
            return False
        for k, v in kwargs.items():
            if hasattr(tpl, k):
                setattr(tpl, k, v)
        import time
        tpl.updated_at = time.time()
        self._persist(tpl)
        return True

    def delete(self, template_id: str) -> bool:
        tpl = self._templates.pop(template_id, None)
        if tpl and self._redis:
            try:
                self._redis.delete(self._redis_key(template_id))
                self._redis.srem(self._redis_index_key(), template_id)
            except Exception:
                pass
        return tpl is not None

    def render(self, template_id: str, **kwargs: str) -> str | None:
        tpl = self._templates.get(template_id)
        if not tpl:
            return None
        result = tpl.render(**kwargs)
        self._persist(tpl)  # update usage_count
        return result

    # ── internals ─────────────────────────────────────────────────────────────

    def _persist(self, tpl: PromptTemplate) -> None:
        if not self._redis:
            return
        try:
            self._redis.setex(
                self._redis_key(tpl.template_id),
                _REDIS_TTL,
                json.dumps(tpl.to_dict()),
            )
            self._redis.sadd(self._redis_index_key(), tpl.template_id)
        except Exception as exc:
            logger.warning("Redis persist failed: %s", exc)
