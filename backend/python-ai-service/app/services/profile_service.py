"""
User Profile Service
────────────────────
Builds a dynamic model of the user from every interaction.

The profile is a JSON document with these top-level keys:
  preferences   – inferred style, topics, communication style
  goals         – short-term and long-term goals mentioned
  habits        – recurring patterns (time of use, frequent topics)
  personality   – OCEAN-style signals extracted from language
  context       – rolling summary of what the assistant knows
  stats         – raw counters (interactions, topics seen, etc.)

The profile is updated after every meaningful assistant turn by sending
a lightweight "profile delta" prompt to the active LLM.  The delta is
merged into the existing JSON, so the profile grows incrementally
without needing to reprocess all history.
"""
from __future__ import annotations

import json
import time
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.db.models import UserProfile

logger = get_logger(__name__)

_DEFAULT_PROFILE: dict[str, Any] = {
    "preferences": {
        "communication_style": "neutral",
        "response_length": "medium",
        "topics_of_interest": [],
        "disliked_topics": [],
        "language": "en",
    },
    "goals": {"short_term": [], "long_term": []},
    "habits": {"peak_usage_hours": [], "frequent_topics": [], "task_patterns": []},
    "personality": {
        "openness": 0.5,
        "conscientiousness": 0.5,
        "extraversion": 0.5,
        "agreeableness": 0.5,
        "neuroticism": 0.5,
    },
    "context": "",
    "stats": {"total_interactions": 0, "topics_seen": [], "skills_used": []},
}

# Minimum gap between full LLM profile updates (seconds) to avoid spam
_UPDATE_COOLDOWN = 30


# ─── Public API ───────────────────────────────────────────────────────────────

async def get_or_create(db: AsyncSession, user_id: str = "default") -> dict[str, Any]:
    """Return the user profile, creating a blank one if not found."""
    row = await _get_row(db, user_id)
    if row is None:
        row = UserProfile(
            user_id=user_id,
            profile_json=json.dumps(_DEFAULT_PROFILE),
            created_at=time.time(),
            updated_at=time.time(),
        )
        db.add(row)
        await db.commit()
    return json.loads(row.profile_json)


async def update_from_conversation(
    db: AsyncSession,
    user_message: str,
    assistant_message: str,
    user_id: str = "default",
) -> None:
    """
    Non-blocking profile update: called after each chat turn.
    Attempts an LLM-powered delta; falls back to heuristic update.
    """
    row = await _get_row(db, user_id)
    if row is None:
        await get_or_create(db, user_id)
        row = await _get_row(db, user_id)

    now = time.time()
    profile: dict[str, Any] = json.loads(row.profile_json)  # type: ignore[union-attr]

    # Rate-limit full LLM updates
    last_updated = row.updated_at  # type: ignore[union-attr]
    if now - last_updated < _UPDATE_COOLDOWN:
        # Lightweight heuristic only
        _heuristic_update(profile, user_message)
        await _persist(db, row, profile)  # type: ignore[arg-type]
        return

    # Full LLM-powered delta
    try:
        delta = await _llm_profile_delta(user_message, assistant_message, profile)
        _merge_delta(profile, delta)
    except Exception as exc:
        logger.debug("profile_llm_update_skipped", reason=str(exc))
        _heuristic_update(profile, user_message)

    profile["stats"]["total_interactions"] = profile["stats"].get("total_interactions", 0) + 1
    await _persist(db, row, profile)  # type: ignore[arg-type]


async def patch(
    db: AsyncSession,
    patches: dict[str, Any],
    user_id: str = "default",
) -> dict[str, Any]:
    """Directly merge patches into the profile (used by user via /profile set)."""
    row = await _get_row(db, user_id)
    if row is None:
        await get_or_create(db, user_id)
        row = await _get_row(db, user_id)

    profile = json.loads(row.profile_json)  # type: ignore[union-attr]
    _merge_delta(profile, patches)
    await _persist(db, row, profile)  # type: ignore[arg-type]
    return profile


async def context_summary(db: AsyncSession, user_id: str = "default") -> str:
    """Return a compact profile summary string to inject into chat system prompt."""
    profile = await get_or_create(db, user_id)
    prefs = profile.get("preferences", {})
    goals = profile.get("goals", {})
    context = profile.get("context", "")

    lines: list[str] = []
    if prefs.get("communication_style") and prefs["communication_style"] != "neutral":
        lines.append(f"Communication style: {prefs['communication_style']}")
    if prefs.get("response_length") and prefs["response_length"] != "medium":
        lines.append(f"Preferred response length: {prefs['response_length']}")
    interests = prefs.get("topics_of_interest", [])
    if interests:
        lines.append(f"Interests: {', '.join(interests[:5])}")
    st_goals = goals.get("short_term", [])
    if st_goals:
        lines.append(f"Current goals: {', '.join(str(g) for g in st_goals[:3])}")
    if context:
        lines.append(f"Context: {context[:300]}")

    return "\n".join(lines) if lines else ""


# ─── Internals ────────────────────────────────────────────────────────────────

async def _get_row(db: AsyncSession, user_id: str) -> UserProfile | None:
    result = await db.execute(select(UserProfile).where(UserProfile.user_id == user_id))
    return result.scalar_one_or_none()


async def _persist(db: AsyncSession, row: UserProfile, profile: dict[str, Any]) -> None:
    row.profile_json = json.dumps(profile)
    row.updated_at = time.time()
    row.total_interactions = profile["stats"].get("total_interactions", row.total_interactions)
    await db.commit()


async def _llm_profile_delta(
    user_msg: str,
    assistant_msg: str,
    current_profile: dict[str, Any],
) -> dict[str, Any]:
    from app.providers.router import ProviderRouter

    pr = ProviderRouter.get()
    provider = pr.get_active_provider()
    if provider is None:
        return {}

    system = (
        "You are a user-modeling agent. Given a conversation turn and the current "
        "user profile, output ONLY a JSON object with keys that should be updated. "
        "Keep the delta minimal — only include keys where you have new signal. "
        "Valid top-level keys: preferences, goals, habits, personality, context. "
        "Do not include 'stats'. Output valid JSON only, no markdown."
    )
    user_content = (
        f"User said: {user_msg[:400]}\n"
        f"Assistant replied: {assistant_msg[:400]}\n"
        f"Current profile summary: {json.dumps(current_profile, indent=None)[:800]}\n\n"
        "Output the JSON delta:"
    )
    result = await provider.chat(
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user_content},
        ],
        model_id="",
        max_tokens=512,
    )
    raw = result.get("choices", [{}])[0].get("message", {}).get("content", "")
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1].lstrip("json").strip()
    return json.loads(raw) if raw else {}


def _heuristic_update(profile: dict[str, Any], user_msg: str) -> None:
    """Cheap keyword scan — no LLM call required."""
    msg_lower = user_msg.lower()

    # Response-length preference signals
    if any(w in msg_lower for w in ("brief", "short", "tl;dr", "concise")):
        profile["preferences"]["response_length"] = "short"
    elif any(w in msg_lower for w in ("detail", "elaborate", "explain fully")):
        profile["preferences"]["response_length"] = "long"


def _merge_delta(base: dict[str, Any], delta: dict[str, Any]) -> None:
    """Deep-merge delta into base (additive, never deletes keys)."""
    for key, value in delta.items():
        if key not in base:
            base[key] = value
        elif isinstance(base[key], dict) and isinstance(value, dict):
            _merge_delta(base[key], value)
        elif isinstance(base[key], list) and isinstance(value, list):
            # Append new items, cap at 50 to avoid unbounded growth
            existing = set(str(i) for i in base[key])
            for item in value:
                if str(item) not in existing:
                    base[key].append(item)
                    existing.add(str(item))
            base[key] = base[key][-50:]
        else:
            base[key] = value
