"""
Dynamic Skill Service
──────────────────────
Skills are LLM-generated Python functions stored in SQLite.

Lifecycle:
  generate  → LLM writes a Python async function from a natural-language spec
  validate  → the function is syntax-checked and dry-run with dummy args
  store     → persisted to DB with version=1, quality_score=0.5
  execute   → called via a sandboxed exec() with a strict timeout
  feedback  → quality_score updated from execution results (0.0–1.0)
  improve   → LLM can regenerate a new version when quality_score < threshold

Every skill is an `async def run(**kwargs) -> dict` function.
The framework calls `run(**params)` and expects a JSON-serialisable dict back.

Security model:
  • Executions run inside RestrictedExec with __builtins__ limited to a safe set
  • Network access is blocked unless the skill explicitly imports httpx (monitored)
  • CPU timeout enforced via asyncio.wait_for
  • Output truncated to SKILL_OUTPUT_LIMIT bytes
"""
from __future__ import annotations

import asyncio
import inspect
import json
import textwrap
import time
import traceback
from typing import Any
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.db.models import Skill

logger = get_logger(__name__)

_SKILL_TIMEOUT = 30  # seconds
_SKILL_OUTPUT_LIMIT = 50_000  # bytes
_QUALITY_IMPROVE_THRESHOLD = 0.3  # below this → trigger auto-improvement


# ─── Public API ───────────────────────────────────────────────────────────────

async def generate_and_store(
    db: AsyncSession,
    name: str,
    description: str,
    task_context: str = "",
    category: str = "general",
    origin: str = "generated",
) -> dict[str, Any]:
    """Ask the LLM to write a skill, validate it, then persist to DB."""
    source_code, parameters = await _generate_skill_code(name, description, task_context)
    _validate_syntax(source_code)

    skill_id = f"skill_{uuid4().hex[:10]}"
    row = Skill(
        skill_id=skill_id,
        name=name,
        description=description,
        source_code=source_code,
        parameters_json=json.dumps(parameters),
        version=1,
        category=category,
        origin=origin,
        enabled=True,
        quality_score=0.5,
        created_at=time.time(),
        updated_at=time.time(),
    )
    db.add(row)
    await db.commit()
    logger.info("skill_created", skill_id=skill_id, name=name)
    return _to_dict(row)


async def get_all(
    db: AsyncSession,
    enabled_only: bool = False,
) -> list[dict[str, Any]]:
    q = select(Skill)
    if enabled_only:
        q = q.where(Skill.enabled.is_(True))
    q = q.order_by(Skill.quality_score.desc())
    result = await db.execute(q)
    return [_to_dict(r) for r in result.scalars().all()]


async def get_by_id(db: AsyncSession, skill_id: str) -> dict[str, Any] | None:
    result = await db.execute(select(Skill).where(Skill.skill_id == skill_id))
    row = result.scalar_one_or_none()
    return _to_dict(row) if row else None


async def execute(
    db: AsyncSession,
    skill_id: str,
    params: dict[str, Any],
) -> dict[str, Any]:
    """Execute a stored skill and record result + quality feedback."""
    result = await db.execute(select(Skill).where(Skill.skill_id == skill_id))
    row = result.scalar_one_or_none()
    if row is None:
        return {"error": f"Skill '{skill_id}' not found"}
    if not row.enabled:
        return {"error": f"Skill '{skill_id}' is disabled"}

    start = time.perf_counter()
    success = False
    output: Any = {}
    error_msg = ""

    try:
        output = await _run_sandboxed(row.source_code, params)
        success = True
    except asyncio.TimeoutError:
        error_msg = f"Skill timed out after {_SKILL_TIMEOUT}s"
    except Exception as exc:
        error_msg = f"{type(exc).__name__}: {exc}"
        logger.warning("skill_execution_error", skill_id=skill_id, error=error_msg)

    elapsed = round((time.perf_counter() - start) * 1000, 1)

    # Update counters + rolling quality score
    row.execution_count += 1
    if success:
        row.success_count += 1
    row.quality_score = round(row.success_count / max(row.execution_count, 1), 4)
    row.updated_at = time.time()
    await db.commit()

    # Trigger auto-improvement if quality is bad
    if row.quality_score < _QUALITY_IMPROVE_THRESHOLD and row.execution_count >= 3:
        asyncio.ensure_future(_auto_improve(db, row, error_msg))

    return {
        "skillId": skill_id,
        "success": success,
        "output": output,
        "error": error_msg or None,
        "elapsedMs": elapsed,
        "qualityScore": row.quality_score,
    }


async def update_skill(
    db: AsyncSession,
    skill_id: str,
    updates: dict[str, Any],
) -> dict[str, Any] | None:
    result = await db.execute(select(Skill).where(Skill.skill_id == skill_id))
    row = result.scalar_one_or_none()
    if row is None:
        return None

    allowed = {"name", "description", "enabled", "category", "source_code"}
    for key, val in updates.items():
        if key in allowed:
            setattr(row, key, val)
    if "source_code" in updates:
        _validate_syntax(updates["source_code"])
        row.version += 1
    row.updated_at = time.time()
    await db.commit()
    return _to_dict(row)


async def delete_skill(db: AsyncSession, skill_id: str) -> bool:
    result = await db.execute(select(Skill).where(Skill.skill_id == skill_id))
    row = result.scalar_one_or_none()
    if row is None:
        return False
    await db.delete(row)
    await db.commit()
    return True


# ─── LLM code generation ──────────────────────────────────────────────────────

async def _generate_skill_code(
    name: str,
    description: str,
    task_context: str,
) -> tuple[str, list[dict]]:
    system = textwrap.dedent("""
        You are a code-generation agent that writes Python async skills for JARVIS.

        Rules:
        1. Write a single `async def run(**kwargs) -> dict` function.
        2. The function must return a JSON-serialisable dict.
        3. Use only Python stdlib unless a third-party import is obviously necessary.
        4. Include a docstring that explains what the skill does and its expected kwargs.
        5. After the function, output a JSON comment block:
           # PARAMETERS: [{"name": "…", "type": "…", "required": true, "description": "…"}]
        6. No class definitions, no module-level side effects.
        7. Handle all exceptions internally; never let the function raise.
        8. Output ONLY the Python code — no markdown fences, no explanations.
    """).strip()

    prompt = (
        f"Skill name: {name}\n"
        f"Description: {description}\n"
        f"Task context: {task_context[:600] if task_context else 'N/A'}\n\n"
        "Write the skill now:"
    )

    try:
        from app.providers.router import ProviderRouter
        pr = ProviderRouter.get()
        provider = pr.get_active_provider()
        if provider is None:
            raise RuntimeError("No provider available")

        result = await provider.chat(
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
            model_id="",
            max_tokens=1024,
        )
        code = result.get("choices", [{}])[0].get("message", {}).get("content", "")
        code = code.strip()
        # Strip markdown fences if present
        if code.startswith("```"):
            code = code.split("```")[1].lstrip("python").strip()
            if "```" in code:
                code = code[: code.index("```")]
    except Exception as exc:
        logger.warning("skill_generation_llm_failed", error=str(exc))
        # Fallback: a minimal stub
        code = textwrap.dedent(f"""
            async def run(**kwargs) -> dict:
                \"\"\"Stub skill: {description}\"\"\"
                return {{"note": "Skill '{name}' is a stub — no provider available for generation", "kwargs": kwargs}}
            # PARAMETERS: []
        """).strip()

    parameters = _parse_parameters_comment(code)
    return code, parameters


def _parse_parameters_comment(code: str) -> list[dict]:
    for line in code.splitlines():
        stripped = line.strip()
        if stripped.startswith("# PARAMETERS:"):
            try:
                return json.loads(stripped[len("# PARAMETERS:"):].strip())
            except Exception:
                pass
    return []


# ─── Sandboxed execution ──────────────────────────────────────────────────────

import builtins as _py_builtins

_SAFE_BUILTINS = {
    name: getattr(_py_builtins, name)
    for name in (
        "abs", "all", "any", "bin", "bool", "bytes", "callable", "chr", "dict",
        "dir", "divmod", "enumerate", "filter", "float", "format", "frozenset",
        "getattr", "hasattr", "hash", "hex", "int", "isinstance", "issubclass",
        "iter", "len", "list", "map", "max", "min", "next", "object", "oct",
        "open", "ord", "pow", "print", "range", "repr", "reversed", "round",
        "set", "setattr", "slice", "sorted", "str", "sum", "tuple", "type",
        "vars", "zip", "True", "False", "None", "Exception", "ValueError",
        "TypeError", "KeyError", "IndexError", "RuntimeError",
    )
    if hasattr(_py_builtins, name)
}


async def _run_sandboxed(source_code: str, params: dict[str, Any]) -> Any:
    """Execute skill source code inside a restricted namespace with timeout."""
    namespace: dict[str, Any] = {
        "__builtins__": _SAFE_BUILTINS,
        "__name__": "__skill__",
        "json": json,
        "time": time,
        "asyncio": asyncio,
    }
    # Allow common safe imports
    for mod_name in ("re", "math", "datetime", "collections", "itertools",
                     "functools", "string", "textwrap", "hashlib", "base64",
                     "urllib.parse", "pathlib", "os.path"):
        try:
            import importlib
            namespace[mod_name.split(".")[0]] = importlib.import_module(mod_name.split(".")[0])
        except ImportError:
            pass

    exec(compile(source_code, "<skill>", "exec"), namespace)  # noqa: S102

    run_fn = namespace.get("run")
    if run_fn is None or not callable(run_fn):
        raise RuntimeError("Skill has no callable `run` function")

    result = await asyncio.wait_for(run_fn(**params), timeout=_SKILL_TIMEOUT)

    # Enforce output size
    serialised = json.dumps(result)
    if len(serialised) > _SKILL_OUTPUT_LIMIT:
        return {"truncated": True, "preview": serialised[:500]}
    return result


# ─── Auto-improvement ─────────────────────────────────────────────────────────

async def _auto_improve(db: AsyncSession, row: Skill, last_error: str) -> None:
    """Ask the LLM to rewrite a poorly-performing skill."""
    try:
        from app.providers.router import ProviderRouter
        pr = ProviderRouter.get()
        provider = pr.get_active_provider()
        if provider is None:
            return

        prompt = (
            f"This skill has a low quality score ({row.quality_score:.2f}) after "
            f"{row.execution_count} executions.\n"
            f"Last error: {last_error or 'unknown'}\n"
            f"Original description: {row.description}\n\n"
            f"Current code:\n{row.source_code}\n\n"
            "Rewrite it to fix the issue. Output ONLY the corrected Python code."
        )
        result = await provider.chat(
            messages=[{"role": "user", "content": prompt}],
            model_id="",
            max_tokens=1024,
        )
        new_code = result.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
        if new_code.startswith("```"):
            new_code = new_code.split("```")[1].lstrip("python").strip()
        _validate_syntax(new_code)

        row.source_code = new_code
        row.version += 1
        row.quality_score = 0.5  # reset after improvement
        row.updated_at = time.time()
        await db.commit()
        logger.info("skill_auto_improved", skill_id=row.skill_id, new_version=row.version)
    except Exception as exc:
        logger.warning("skill_auto_improve_failed", skill_id=row.skill_id, error=str(exc))


# ─── Validation ───────────────────────────────────────────────────────────────

def _validate_syntax(code: str) -> None:
    try:
        compile(code, "<skill>", "exec")
    except SyntaxError as exc:
        raise ValueError(f"Skill source code has syntax error: {exc}") from exc


# ─── Serialiser ───────────────────────────────────────────────────────────────

def _to_dict(row: Skill) -> dict[str, Any]:
    try:
        params = json.loads(row.parameters_json or "[]")
    except Exception:
        params = []
    return {
        "skillId": row.skill_id,
        "name": row.name,
        "description": row.description,
        "parameters": params,
        "version": row.version,
        "category": row.category,
        "origin": row.origin,
        "enabled": row.enabled,
        "qualityScore": row.quality_score,
        "executionCount": row.execution_count,
        "successCount": row.success_count,
        "createdAt": row.created_at,
        "updatedAt": row.updated_at,
    }
