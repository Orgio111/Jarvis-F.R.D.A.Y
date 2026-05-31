"""IntentRouter — trigger-based skill dispatch.

Matches a user message against skills' ``triggers_json`` field before the LLM
is consulted, enabling zero-latency skill invocation for well-known commands.

Trigger types
─────────────
• Keyword trigger  — any string not starting with ``/``.
  Matched via case-insensitive substring search in the user message.
  e.g. ``"weather forecast"`` matches *"what's the weather forecast in Ulaanbaatar?"*

• Slash trigger    — string starting with ``/``.
  Matched when the user message (stripped) **starts with** that prefix
  (case-insensitive).
  e.g. ``"/run"`` matches *"/run tests"* or *"/run"*.

Ranking
───────
When multiple skills match, they are sorted by ``quality_score`` descending;
the top match is returned.

Usage
─────
    router = IntentRouter(db)
    match = await router.match(user_message)
    if match:
        # match is a dict with keys: skill_id, name, triggers, quality_score
        skill_result = await skill_service.execute(db, match["skill_id"], params)
"""
from __future__ import annotations

import json
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.db.models import Skill

logger = get_logger(__name__)


class IntentRouter:
    """Stateless per-request intent router.

    Parameters
    ----------
    db:
        Active async SQLAlchemy session.
    """

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    # ── Public API ─────────────────────────────────────────────────────────────

    async def match(self, message: str) -> dict[str, Any] | None:
        """Return the best matching skill dict, or None.

        Algorithm
        ---------
        1. Load all enabled skills that have at least one trigger.
        2. For each skill iterate its triggers:
           - Slash trigger  → message (stripped, lowercased) starts with trigger.
           - Keyword trigger → trigger (lowercased) is a substring of message (lowercased).
        3. Collect all matching skills, sort by quality_score desc.
        4. Return the first match as a plain dict, or None if no match.
        """
        needle = message.strip().lower()
        if not needle:
            return None

        # Only load skills that have non-empty triggers
        q = (
            select(Skill)
            .where(Skill.enabled.is_(True))
            .order_by(Skill.quality_score.desc())
        )
        result = await self._db.execute(q)
        skills = result.scalars().all()

        candidates: list[tuple[float, dict[str, Any]]] = []

        for skill in skills:
            triggers = self._parse_triggers(skill.triggers_json)
            if not triggers:
                continue

            if self._skill_matches(needle, triggers):
                candidates.append((
                    skill.quality_score,
                    self._to_dict(skill, triggers),
                ))

        if not candidates:
            return None

        # Sort by quality_score desc, pick best
        candidates.sort(key=lambda x: x[0], reverse=True)
        best_score, best_skill = candidates[0]
        logger.info(
            "intent_router_match",
            skill_id=best_skill["skill_id"],
            name=best_skill["name"],
            quality_score=best_score,
            candidate_count=len(candidates),
        )
        return best_skill

    async def all_triggers(self) -> dict[str, list[str]]:
        """Return mapping of skill_id → triggers for all enabled skills."""
        q = select(Skill).where(Skill.enabled.is_(True))
        result = await self._db.execute(q)
        out: dict[str, list[str]] = {}
        for skill in result.scalars().all():
            triggers = self._parse_triggers(skill.triggers_json)
            if triggers:
                out[skill.skill_id] = triggers
        return out

    # ── Helpers ────────────────────────────────────────────────────────────────

    @staticmethod
    def _parse_triggers(triggers_json: str) -> list[str]:
        try:
            parsed = json.loads(triggers_json or "[]")
            if isinstance(parsed, list):
                return [str(t).strip() for t in parsed if str(t).strip()]
        except (json.JSONDecodeError, TypeError):
            pass
        return []

    @staticmethod
    def _skill_matches(needle: str, triggers: list[str]) -> bool:
        """Return True if any trigger matches the needle."""
        for trigger in triggers:
            t_lower = trigger.lower()
            if t_lower.startswith("/"):
                # Slash command: must be a prefix of the message
                if needle.startswith(t_lower):
                    return True
            else:
                # Keyword: substring match
                if t_lower in needle:
                    return True
        return False

    @staticmethod
    def _to_dict(skill: Skill, triggers: list[str]) -> dict[str, Any]:
        try:
            deps = json.loads(skill.dependencies_json or "[]")
        except Exception:
            deps = []
        return {
            "skill_id": skill.skill_id,
            "name": skill.name,
            "description": skill.description,
            "triggers": triggers,
            "dependencies": deps,
            "quality_score": skill.quality_score,
            "category": skill.category,
            "origin": skill.origin,
        }
