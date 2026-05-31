"""
Skill Registry Service
──────────────────────
Manages skill scoring, ranking, health checks, and the self-growing capability
detection loop.

Score formula (Skill OS spec):
  trust_score = success_rate * 0.5
              + usage_frequency * 0.2   (normalised 0-1 vs top skill)
              + speed_score     * 0.2   (1 - clamp(latency_ms / 10000, 0, 1))
              + user_feedback   * 0.1   (user_rating / 5.0)
"""
from __future__ import annotations

import hashlib
import json
import time
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.db.models import Skill

logger = get_logger(__name__)

# Thresholds
_AUTO_DISABLE_TRUST = 0.15   # below this after MIN_RUNS → disable
_AUTO_DISABLE_MIN_RUNS = 5   # only act after enough data
_LATENCY_WORST_MS = 10_000   # 10 s → speed_score = 0


# ─── Score computation ────────────────────────────────────────────────────────

def compute_trust_score(skill: Skill, max_usage_count: int = 1) -> float:
    """Weighted formula → 0.0-1.0."""
    # Success rate component
    total = skill.execution_count or 1
    success_rate = (skill.success_count / total)

    # Usage frequency (normalised vs most-used skill in registry)
    usage_freq = min(skill.execution_count / max(max_usage_count, 1), 1.0)

    # Speed score: faster = higher
    latency = skill.latency_ms_avg or 0.0
    speed_score = 1.0 - min(latency / _LATENCY_WORST_MS, 1.0)

    # User feedback (0-5 → 0-1)
    feedback = (skill.user_rating / 5.0) if skill.rating_count > 0 else 0.5  # neutral prior

    score = (
        success_rate * 0.5
        + usage_freq   * 0.2
        + speed_score  * 0.2
        + feedback     * 0.1
    )
    return round(min(max(score, 0.0), 1.0), 4)


# ─── Post-execution update ────────────────────────────────────────────────────

async def update_after_execution(
    db: AsyncSession,
    skill_id: str,
    success: bool,
    latency_ms: float,
) -> dict[str, Any] | None:
    """Update counters + rolling latency + recompute trust_score after each run."""
    result = await db.execute(select(Skill).where(Skill.skill_id == skill_id))
    skill = result.scalar_one_or_none()
    if skill is None:
        return None

    # Counters
    skill.execution_count += 1
    if success:
        skill.success_count += 1

    # Rolling average latency (exponential moving average, α=0.3)
    if skill.latency_ms_avg == 0.0:
        skill.latency_ms_avg = latency_ms
    else:
        skill.latency_ms_avg = 0.7 * skill.latency_ms_avg + 0.3 * latency_ms

    # Recompute trust_score — need max_usage_count for normalisation
    max_count_result = await db.execute(select(func.max(Skill.execution_count)))
    max_count = max_count_result.scalar_one() or 1

    skill.trust_score = compute_trust_score(skill, max_usage_count=max_count)
    skill.quality_score = skill.trust_score  # keep legacy field in sync
    skill.updated_at = time.time()

    await db.commit()
    logger.info(
        "skill_registry_updated",
        skill_id=skill_id,
        trust_score=skill.trust_score,
        execution_count=skill.execution_count,
        latency_ms_avg=round(skill.latency_ms_avg, 1),
    )

    # Auto-disable if consistently failing
    if (
        skill.execution_count >= _AUTO_DISABLE_MIN_RUNS
        and skill.trust_score < _AUTO_DISABLE_TRUST
        and skill.enabled
    ):
        skill.enabled = False
        await db.commit()
        logger.warning(
            "skill_auto_disabled",
            skill_id=skill_id,
            trust_score=skill.trust_score,
            runs=skill.execution_count,
        )

    return _to_summary(skill)


async def submit_rating(
    db: AsyncSession,
    skill_id: str,
    rating: float,  # 1.0–5.0
) -> dict[str, Any] | None:
    """Add a user rating and recompute trust_score."""
    rating = max(1.0, min(5.0, rating))
    result = await db.execute(select(Skill).where(Skill.skill_id == skill_id))
    skill = result.scalar_one_or_none()
    if skill is None:
        return None

    # Rolling average of ratings
    total_rating = skill.user_rating * skill.rating_count + rating
    skill.rating_count += 1
    skill.user_rating = total_rating / skill.rating_count

    # Recompute trust
    max_count_result = await db.execute(select(func.max(Skill.execution_count)))
    max_count = max_count_result.scalar_one() or 1
    skill.trust_score = compute_trust_score(skill, max_usage_count=max_count)
    skill.quality_score = skill.trust_score
    skill.updated_at = time.time()
    await db.commit()

    logger.info("skill_rated", skill_id=skill_id, rating=rating, new_avg=skill.user_rating)
    return _to_summary(skill)


# ─── Ranking ──────────────────────────────────────────────────────────────────

async def rank_skills(
    db: AsyncSession,
    category: str | None = None,
    limit: int = 50,
    enabled_only: bool = True,
) -> list[dict[str, Any]]:
    """Return skills sorted by trust_score desc."""
    q = select(Skill)
    if enabled_only:
        q = q.where(Skill.enabled.is_(True))
    if category:
        q = q.where(Skill.category == category)
    q = q.order_by(Skill.trust_score.desc()).limit(limit)
    result = await db.execute(q)
    return [_to_full_dict(s) for s in result.scalars().all()]


async def trending_skills(
    db: AsyncSession,
    limit: int = 20,
) -> list[dict[str, Any]]:
    """Top skills by trust_score * usage_count (popularity weighted)."""
    q = (
        select(Skill)
        .where(Skill.enabled.is_(True))
        .where(Skill.execution_count > 0)
        .order_by((Skill.trust_score * Skill.execution_count).desc())
        .limit(limit)
    )
    result = await db.execute(q)
    return [_to_full_dict(s) for s in result.scalars().all()]


async def search_skills(
    db: AsyncSession,
    query: str = "",
    tags: list[str] | None = None,
    category: str | None = None,
    limit: int = 30,
) -> list[dict[str, Any]]:
    """Keyword search on name + description + tags."""
    q = select(Skill).where(Skill.enabled.is_(True))
    if category:
        q = q.where(Skill.category == category)

    result = await db.execute(q.order_by(Skill.trust_score.desc()))
    skills = result.scalars().all()

    if not query and not tags:
        return [_to_full_dict(s) for s in skills[:limit]]

    # In-process filter (SQLite has no FTS without extension)
    needle = query.lower().strip()
    wanted_tags = {t.lower() for t in (tags or [])}
    out = []
    for s in skills:
        s_tags = {t.lower() for t in _parse_json_list(s.tags_json)}
        name_match = needle and (needle in s.name.lower() or needle in s.description.lower())
        tag_match = bool(wanted_tags & s_tags) if wanted_tags else False
        if (needle and name_match) or (wanted_tags and tag_match) or (not needle and not wanted_tags):
            out.append(_to_full_dict(s))
        if len(out) >= limit:
            break
    return out


# ─── Self-growing capability detection ────────────────────────────────────────

async def detect_missing_capability(
    db: AsyncSession,
    user_message: str,
    llm_response: str,
) -> str | None:
    """
    Returns a capability description string if a missing-skill signal is detected,
    otherwise None.

    Heuristics:
    - LLM response contains "I can't", "I don't have the ability", "no tool for",
      "I'm unable to", "I cannot" — extract the task noun phrase.
    - IntentRouter returned None (no trigger matched) — already handled upstream.
    """
    MISSING_SIGNALS = [
        "i can't", "i cannot", "i don't have the ability", "no tool for",
        "i'm unable to", "i am unable to", "i lack the ability",
        "no skill", "no capability", "not able to",
    ]
    lowered = llm_response.lower()
    if not any(sig in lowered for sig in MISSING_SIGNALS):
        return None

    # Attempt to extract the missing capability from the user message
    # Simple heuristic: return first ~80 chars of user message as the capability hint
    cap = user_message.strip()[:120]
    logger.info("missing_capability_detected", capability_hint=cap)
    return cap


def compute_hash(source_code: str) -> str:
    return hashlib.sha256(source_code.encode()).hexdigest()


# ─── Internal helpers ─────────────────────────────────────────────────────────

def _parse_json_list(raw: str) -> list[str]:
    try:
        v = json.loads(raw or "[]")
        return v if isinstance(v, list) else []
    except Exception:
        return []


def _to_summary(skill: Skill) -> dict[str, Any]:
    return {
        "skill_id": skill.skill_id,
        "name": skill.name,
        "trust_score": skill.trust_score,
        "execution_count": skill.execution_count,
        "success_count": skill.success_count,
        "latency_ms_avg": round(skill.latency_ms_avg, 1),
        "user_rating": round(skill.user_rating, 2),
        "rating_count": skill.rating_count,
        "enabled": skill.enabled,
    }


def _to_full_dict(skill: Skill) -> dict[str, Any]:
    return {
        "skill_id": skill.skill_id,
        "name": skill.name,
        "description": skill.description,
        "category": skill.category,
        "origin": skill.origin,
        "version": skill.version,
        "enabled": skill.enabled,
        "published": skill.published,
        "publisher": skill.publisher,
        "repo_url": skill.repo_url,
        "hash_sha": skill.hash_sha,
        "trust_score": skill.trust_score,
        "quality_score": skill.quality_score,
        "execution_count": skill.execution_count,
        "success_count": skill.success_count,
        "latency_ms_avg": round(skill.latency_ms_avg, 1),
        "user_rating": round(skill.user_rating, 2),
        "rating_count": skill.rating_count,
        "tags": _parse_json_list(skill.tags_json),
        "triggers": _parse_json_list(skill.triggers_json),
        "dependencies": _parse_json_list(skill.dependencies_json),
        "previous_version_id": skill.previous_version_id,
        "installed_at": skill.installed_at,
        "created_at": skill.created_at,
        "updated_at": skill.updated_at,
    }
