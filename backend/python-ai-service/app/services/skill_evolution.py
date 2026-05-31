"""
Skill Evolution Loop
──────────────────────
Monitors skill health and automatically patches failing skills.

Evolution cycle (runs every 10 min via APScheduler):
  1. Scan all enabled skills with trust_score < EVOLVE_THRESHOLD and execution_count >= MIN_RUNS
  2. For each failing skill: ask LLM to patch/rewrite based on recent error context
  3. New version stored with previous_version_id pointing to old skill
  4. Old skill deprecated (enabled=False, name suffixed with "[deprecated]")
  5. Emit log events for observability

Version chain: skill_v1 → skill_v2 → skill_v3 (each knows previous_version_id)
"""
from __future__ import annotations

import json
import time
import textwrap
from typing import Any
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.db.models import Skill

logger = get_logger(__name__)

_EVOLVE_THRESHOLD = 0.35   # trust_score below this triggers evolution
_EVOLVE_MIN_RUNS = 3       # only after enough data
_EVOLVE_MAX_PER_CYCLE = 5  # max skills to evolve per run (rate limit LLM)


# ─── Public API ───────────────────────────────────────────────────────────────

async def run_evolution_cycle(db: AsyncSession) -> dict[str, Any]:
    """
    Scan failing skills, patch them. Called by APScheduler every 10 min.
    Returns summary dict.
    """
    q = (
        select(Skill)
        .where(Skill.enabled.is_(True))
        .where(Skill.trust_score < _EVOLVE_THRESHOLD)
        .where(Skill.execution_count >= _EVOLVE_MIN_RUNS)
        .order_by(Skill.trust_score.asc())
        .limit(_EVOLVE_MAX_PER_CYCLE)
    )
    result = await db.execute(q)
    candidates = result.scalars().all()

    if not candidates:
        logger.info("evolution_cycle_nothing_to_evolve")
        return {"evolved": 0, "skipped": 0}

    evolved = 0
    skipped = 0
    for skill in candidates:
        try:
            await patch_skill(db, skill)
            evolved += 1
        except Exception as e:
            logger.warning("evolution_patch_failed", skill_id=skill.skill_id, error=str(e))
            skipped += 1

    logger.info("evolution_cycle_done", evolved=evolved, skipped=skipped)
    return {"evolved": evolved, "skipped": skipped}


async def patch_skill(
    db: AsyncSession,
    skill: Skill,
    error_context: str = "",
) -> dict[str, Any]:
    """
    Ask LLM to rewrite a failing skill. Creates new version, deprecates old.
    """
    logger.info("evolution_patching", skill_id=skill.skill_id, trust_score=skill.trust_score)

    new_code = await _llm_patch_skill(skill, error_context)

    # Validate syntax
    import ast
    try:
        ast.parse(new_code)
    except SyntaxError as e:
        raise ValueError(f"LLM patch has syntax error: {e}")

    # Deprecate old skill
    old_name = skill.name
    skill.enabled = False
    skill.name = f"{old_name} [deprecated v{skill.version}]"
    skill.updated_at = time.time()

    # Create new version
    import hashlib
    new_skill_id = f"skill_ev_{uuid4().hex[:10]}"
    now = time.time()
    new_skill = Skill(
        skill_id=new_skill_id,
        name=old_name,
        description=skill.description + " [auto-evolved]",
        source_code=new_code,
        parameters_json=skill.parameters_json,
        version=skill.version + 1,
        category=skill.category,
        origin="evolved",
        enabled=True,
        quality_score=0.5,
        trust_score=0.5,
        triggers_json=skill.triggers_json,
        dependencies_json=skill.dependencies_json,
        tags_json=skill.tags_json,
        publisher=skill.publisher,
        repo_url=skill.repo_url,
        hash_sha=hashlib.sha256(new_code.encode()).hexdigest(),
        previous_version_id=skill.skill_id,
        created_at=now,
        updated_at=now,
    )
    db.add(new_skill)
    await db.commit()

    logger.info(
        "evolution_new_version_deployed",
        old_skill_id=skill.skill_id,
        new_skill_id=new_skill_id,
        version=new_skill.version,
    )

    from app.services.skill_registry import _to_full_dict
    return _to_full_dict(new_skill)


async def get_version_chain(
    db: AsyncSession,
    skill_id: str,
) -> list[dict[str, Any]]:
    """Return full version history for a skill (newest first)."""
    from app.services.skill_registry import _to_full_dict

    chain = []
    current_id = skill_id
    seen = set()

    while current_id and current_id not in seen:
        seen.add(current_id)
        result = await db.execute(select(Skill).where(Skill.skill_id == current_id))
        skill = result.scalar_one_or_none()
        if skill is None:
            break
        chain.append(_to_full_dict(skill))
        current_id = skill.previous_version_id  # type: ignore

    return chain


# ─── LLM patching ─────────────────────────────────────────────────────────────

async def _llm_patch_skill(skill: Skill, error_context: str) -> str:
    """Ask LLM to rewrite the skill source_code to fix the issue."""
    prompt = textwrap.dedent(f"""
        You are Jarvis, an AI system that improves its own skills.

        The following skill has a low success rate (trust_score={skill.trust_score:.2f},
        success={skill.success_count}/{skill.execution_count} runs).

        Skill name: {skill.name}
        Description: {skill.description}
        Recent error context: {error_context or 'not available'}

        Current source code:
        ```python
        {skill.source_code}
        ```

        Write an improved version of the `async def run(**kwargs) -> dict` function.
        Rules:
        - Must be a valid Python async function named `run` that takes **kwargs and returns dict
        - Fix the likely cause of failure
        - Keep the same interface (same inputs, same output keys if possible)
        - Add defensive error handling (try/except returning {{"error": str(e), "success": False}})
        - Output ONLY the Python code, no prose, no markdown fences

        Improved code:
    """).strip()

    from app.agents.base_agent import BaseAgent, AgentResult
    from app.agents.free_model_pool import AgentRole

    class _PatchAgent(BaseAgent):
        role = AgentRole.EDITOR
        async def _execute(self, ctx: dict) -> AgentResult:
            text, model = await self._chat(
                [{"role": "user", "content": ctx["prompt"]}],
                temperature=0.15,
                max_tokens=1024,
            )
            return AgentResult(role=self.role, success=True, content=text, model_used=model)

    agent = _PatchAgent()
    result = await agent.run({"prompt": prompt})
    raw = result.content.strip()

    # Strip markdown fences if LLM added them
    for fence in ("```python", "```"):
        if raw.startswith(fence):
            raw = raw[len(fence):]
            break
    if raw.endswith("```"):
        raw = raw[:-3]

    return raw.strip()
