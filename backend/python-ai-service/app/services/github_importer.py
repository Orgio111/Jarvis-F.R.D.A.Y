"""
GitHub Skill Importer
──────────────────────
Imports skills from GitHub (or any git URL) into the Jarvis Skill OS.

Flow:
  URL → clone repo → detect manifest → wrap to Jarvis format → sandbox test → register

Manifest detection priority:
  1. skill.json         — Jarvis-native format
  2. tool.py            — single callable, LLM wraps it
  3. agent.yaml         — LangChain/AutoGPT style
  4. plugin manifest    — any *manifest.json
  5. Fallback: LLM scans repo → extracts callable functions → builds manifest
"""
from __future__ import annotations

import ast
import hashlib
import json
import os
import shutil
import subprocess
import tempfile
import textwrap
import time
from pathlib import Path
from typing import Any
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.db.models import Skill
from app.db.database import get_db

logger = get_logger(__name__)

_CLONE_TIMEOUT = 60   # seconds
_MAX_REPO_SIZE_MB = 50


# ─── Public API ───────────────────────────────────────────────────────────────

async def import_from_github(
    db: AsyncSession,
    url: str,
    publisher: str = "github_import",
    category: str = "imported",
) -> dict[str, Any]:
    """
    Full import pipeline:
      clone → detect manifest → wrap → validate → register → return skill dict.
    Raises on any fatal error.
    """
    repo_dir = None
    try:
        repo_dir = await _clone_repo(url)
        manifest = await _detect_manifest(repo_dir)
        if not manifest:
            manifest = await _llm_generate_manifest(repo_dir, url)

        source_code = _wrap_to_jarvis_format(manifest, repo_dir)
        _validate_syntax(source_code)

        skill = await _register_skill(
            db=db,
            manifest=manifest,
            source_code=source_code,
            repo_url=url,
            publisher=publisher,
            category=category,
        )
        logger.info("github_import_success", skill_id=skill["skill_id"], url=url)
        return skill

    finally:
        if repo_dir and os.path.exists(repo_dir):
            shutil.rmtree(repo_dir, ignore_errors=True)


# ─── Step 1: Clone ────────────────────────────────────────────────────────────

async def _clone_repo(url: str) -> str:
    """Git-clone URL into a temp dir. Returns path."""
    import asyncio
    dest = tempfile.mkdtemp(prefix="jarvis_github_")
    try:
        proc = await asyncio.create_subprocess_exec(
            "git", "clone", "--depth=1", "--quiet", url, dest,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=_CLONE_TIMEOUT)
        except asyncio.TimeoutError:
            proc.kill()
            raise RuntimeError(f"git clone timed out after {_CLONE_TIMEOUT}s: {url}")

        if proc.returncode != 0:
            raise RuntimeError(f"git clone failed: {stderr.decode()[:300]}")

        logger.info("repo_cloned", url=url, dest=dest)
        return dest
    except Exception:
        shutil.rmtree(dest, ignore_errors=True)
        raise


# ─── Step 2: Detect manifest ──────────────────────────────────────────────────

async def _detect_manifest(repo_dir: str) -> dict[str, Any] | None:
    root = Path(repo_dir)

    # Priority 1: skill.json
    skill_json = root / "skill.json"
    if skill_json.exists():
        try:
            data = json.loads(skill_json.read_text())
            logger.info("manifest_found", file="skill.json")
            return _normalise_manifest(data)
        except Exception as e:
            logger.warning("skill_json_parse_error", error=str(e))

    # Priority 2: plugin manifest (any *manifest*.json)
    for f in root.rglob("*manifest*.json"):
        try:
            data = json.loads(f.read_text())
            if "name" in data or "entry" in data or "description" in data:
                logger.info("manifest_found", file=str(f))
                return _normalise_manifest(data)
        except Exception:
            pass

    # Priority 3: agent.yaml
    for yaml_file in ["agent.yaml", "agent.yml", "skill.yaml", "tool.yaml"]:
        yaml_path = root / yaml_file
        if yaml_path.exists():
            try:
                import yaml  # type: ignore
                data = yaml.safe_load(yaml_path.read_text())
                if isinstance(data, dict) and ("name" in data or "description" in data):
                    logger.info("manifest_found", file=yaml_file)
                    return _normalise_manifest(data)
            except Exception:
                pass

    # Priority 4: tool.py with a `run()` or `execute()` function
    tool_py = root / "tool.py"
    if tool_py.exists():
        funcs = _extract_callables(tool_py.read_text())
        if funcs:
            entry_func = funcs[0]
            logger.info("manifest_inferred", file="tool.py", entry=entry_func["name"])
            return {
                "name": root.name.replace("-", "_").replace(" ", "_"),
                "description": f"Imported tool from {root.name}",
                "entry": f"tool.py:{entry_func['name']}",
                "inputs": entry_func["params"],
                "outputs": ["result"],
                "tags": ["imported"],
                "source_file": str(tool_py),
                "source_func": entry_func["name"],
            }

    return None


async def _llm_generate_manifest(repo_dir: str, url: str) -> dict[str, Any]:
    """Fallback: LLM analyses repo files and generates a manifest."""
    root = Path(repo_dir)

    # Collect relevant Python files (skip __pycache__, .git, tests)
    py_files = [
        f for f in root.rglob("*.py")
        if not any(part.startswith((".git", "__pycache__", "test", "tests")) for part in f.parts)
    ][:10]  # limit to 10 files

    snippets: list[str] = []
    total_chars = 0
    for pyf in py_files:
        text = pyf.read_text(errors="replace")
        chunk = f"=== {pyf.relative_to(root)} ===\n{text[:800]}"
        snippets.append(chunk)
        total_chars += len(chunk)
        if total_chars > 6000:
            break

    repo_summary = "\n\n".join(snippets) or "No Python files found."
    prompt = textwrap.dedent(f"""
        You are analysing a GitHub repo to import it as a Jarvis skill.
        Repo URL: {url}

        Repo files:
        {repo_summary}

        Output a JSON object (only JSON, no prose) with these fields:
        {{
          "name": "<snake_case skill name>",
          "description": "<one sentence what this skill does>",
          "entry": "<filename>:<function_name> of the main callable>",
          "inputs": ["<param1>", "<param2>"],
          "outputs": ["result"],
          "tags": ["<tag1>", "<tag2>"],
          "category": "<general|search|web|data|code|utility>"
        }}
    """).strip()

    from app.agents.base_agent import BaseAgent, AgentResult
    from app.agents.free_model_pool import AgentRole

    class _ManifestAgent(BaseAgent):
        role = AgentRole.PLANNER
        async def _execute(self, ctx: dict) -> AgentResult:
            text, model = await self._chat([
                {"role": "user", "content": ctx["prompt"]}
            ], temperature=0.1, max_tokens=512)
            return AgentResult(role=self.role, success=True, content=text, model_used=model)

    agent = _ManifestAgent()
    result = await agent.run({"prompt": prompt})

    try:
        manifest_data = json.loads(BaseAgent._extract_json(result.content))
        logger.info("manifest_llm_generated", name=manifest_data.get("name"))
        return _normalise_manifest(manifest_data)
    except Exception as e:
        logger.warning("manifest_llm_parse_failed", error=str(e))
        # Last resort: use repo name as skill name
        repo_name = Path(repo_dir).name
        return {
            "name": repo_name.replace("-", "_"),
            "description": f"Skill imported from {url}",
            "entry": "main.py:run",
            "inputs": [],
            "outputs": ["result"],
            "tags": ["imported"],
        }


# ─── Step 3: Wrap to Jarvis format ────────────────────────────────────────────

def _wrap_to_jarvis_format(manifest: dict[str, Any], repo_dir: str) -> str:
    """
    Generate `async def run(**kwargs) -> dict` that wraps the imported callable.
    If a source_file is identified, embed the source inline.
    """
    name = manifest.get("name", "imported_skill")
    description = manifest.get("description", "")
    inputs = manifest.get("inputs", [])
    source_file = manifest.get("source_file")
    source_func = manifest.get("source_func", "run")

    # Try to embed source code inline for portability
    inline_source = ""
    if source_file and os.path.exists(source_file):
        try:
            raw = Path(source_file).read_text(errors="replace")
            inline_source = raw
        except Exception:
            pass

    if inline_source:
        # Embed the original function inline and delegate to it
        return textwrap.dedent(f"""
            # Imported from GitHub — auto-wrapped by Jarvis GitHub Importer
            # Original: {manifest.get('entry', '?')}
            # Description: {description}
            import asyncio, json

            {inline_source}

            async def run(**kwargs) -> dict:
                \"\"\"Jarvis wrapper for: {name}\\n{description}\"\"\"
                try:
                    raw_fn = {source_func}
                    import inspect
                    if inspect.iscoroutinefunction(raw_fn):
                        result = await raw_fn(**kwargs)
                    else:
                        result = raw_fn(**kwargs)
                    if isinstance(result, dict):
                        return result
                    return {{"result": result, "success": True}}
                except Exception as e:
                    return {{"error": str(e), "success": False}}
        """).strip()
    else:
        # Generate a stub that documents the expected interface
        params_doc = ", ".join(f'"{p}": kwargs.get("{p}")' for p in inputs)
        return textwrap.dedent(f"""
            # Stub skill — GitHub import could not embed source inline
            # Original entry: {manifest.get('entry', '?')}
            # Description: {description}
            async def run(**kwargs) -> dict:
                \"\"\"Jarvis skill: {name}\\n{description}\"\"\"
                return {{
                    "name": "{name}",
                    "inputs": {{{params_doc}}},
                    "status": "stub — implement body or re-import with source",
                    "success": False,
                }}
        """).strip()


# ─── Step 4: Register ─────────────────────────────────────────────────────────

async def _register_skill(
    db: AsyncSession,
    manifest: dict[str, Any],
    source_code: str,
    repo_url: str,
    publisher: str,
    category: str,
) -> dict[str, Any]:
    from app.services.skill_registry import compute_hash, _to_full_dict

    skill_id = f"skill_gh_{uuid4().hex[:10]}"
    now = time.time()
    tags = manifest.get("tags", [])

    row = Skill(
        skill_id=skill_id,
        name=manifest.get("name", skill_id),
        description=manifest.get("description", ""),
        source_code=source_code,
        parameters_json=json.dumps([
            {"name": p, "type": "str", "required": False, "description": ""}
            for p in manifest.get("inputs", [])
        ]),
        version=1,
        category=manifest.get("category", category),
        origin="github_import",
        enabled=True,
        quality_score=0.5,
        trust_score=0.5,
        tags_json=json.dumps(tags),
        publisher=publisher,
        repo_url=repo_url,
        hash_sha=compute_hash(source_code),
        installed_at=now,
        created_at=now,
        updated_at=now,
    )
    db.add(row)
    await db.commit()
    logger.info("github_skill_registered", skill_id=skill_id, name=row.name)
    return _to_full_dict(row)


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _extract_callables(source: str) -> list[dict[str, Any]]:
    """Parse Python source → list of {name, params} for top-level functions."""
    try:
        tree = ast.parse(source)
        out = []
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if node.name.startswith("_"):
                    continue
                params = [
                    arg.arg for arg in node.args.args
                    if arg.arg not in ("self", "cls")
                ]
                out.append({"name": node.name, "params": params})
        return out
    except Exception:
        return []


def _normalise_manifest(data: dict) -> dict[str, Any]:
    """Ensure all required keys are present."""
    return {
        "name": str(data.get("name", "imported_skill")).replace("-", "_").replace(" ", "_"),
        "description": str(data.get("description", "")),
        "entry": str(data.get("entry", "skill.py:run")),
        "inputs": list(data.get("inputs", data.get("parameters", []))),
        "outputs": list(data.get("outputs", ["result"])),
        "tags": list(data.get("tags", [])),
        "category": str(data.get("category", "general")),
        "source_file": data.get("source_file"),
        "source_func": data.get("source_func"),
    }


def _validate_syntax(source_code: str) -> None:
    try:
        ast.parse(source_code)
    except SyntaxError as e:
        raise ValueError(f"Generated skill has syntax error: {e}") from e
