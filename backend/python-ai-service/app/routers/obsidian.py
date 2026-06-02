"""
Obsidian API router.

Endpoints:
  GET  /obsidian/status          — vault info + enabled state
  GET  /obsidian/files           — list all vault files
  GET  /obsidian/read            — read a vault file (?path=swarm/agents.md)
  POST /obsidian/log/agent       — write agent diary entry
  POST /obsidian/log/decision    — write decision log entry
  POST /obsidian/log/memory      — write memory entry (short|long)
  POST /obsidian/log/task        — write task log entry
  POST /obsidian/log/improvement — write self-improvement entry (win|failure)
  GET  /obsidian/graph           — return nodes+edges for graph visualisation
"""
from __future__ import annotations

import os
import re
import logging
from pathlib import Path
from typing import Any, Literal

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse

from app.core.envelopes import error, success

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/obsidian", tags=["obsidian"])


def _obs():
    from app.obsidian.sync import get_obsidian
    return get_obsidian()


# ── Session Replay (nested under /obsidian/replay) ────────────────────────────
from app.routers.session_replay import router as _replay_router
router.include_router(_replay_router, prefix="")


# ── GET /obsidian/status ──────────────────────────────────────────────────────

@router.get("/status")
async def obsidian_status():
    obs = _obs()
    if obs is None:
        return success({"enabled": False, "vault": None, "file_count": 0})

    vault = Path(obs.vault_root)
    files = list(vault.rglob("*.md"))
    return success({
        "enabled": True,
        "vault": str(vault.resolve()),
        "file_count": len(files),
        "size_bytes": sum(f.stat().st_size for f in files if f.exists()),
    })


# ── GET /obsidian/files ───────────────────────────────────────────────────────

@router.get("/files")
async def list_files():
    obs = _obs()
    if obs is None:
        return error("obsidian_disabled", "Obsidian integration is disabled")

    vault = Path(obs.vault_root)
    files = [str(f.relative_to(vault)) for f in sorted(vault.rglob("*.md"))]
    return success({"files": files, "count": len(files)})


# ── GET /obsidian/read ────────────────────────────────────────────────────────

@router.get("/read")
async def read_file(path: str = Query(..., description="Relative vault path, e.g. swarm/agents.md")):
    obs = _obs()
    if obs is None:
        return error("obsidian_disabled", "Obsidian integration is disabled")

    # Security: no path traversal
    if ".." in path or path.startswith("/"):
        return JSONResponse(status_code=400, content=error("invalid_path", "Invalid path"))

    full = obs.writer().abs_path(path)
    if not full.exists():
        return JSONResponse(status_code=404, content=error("not_found", f"{path} not found"))

    content = full.read_text(encoding="utf-8")
    return success({"path": path, "content": content, "size": len(content)})


# ── POST /obsidian/log/agent ──────────────────────────────────────────────────

@router.post("/log/agent")
async def log_agent(body: dict[str, Any]):
    """
    Body: { agent_id, event, detail?, metadata?, tags? }
    """
    obs = _obs()
    if obs is None:
        return success({"written": False, "reason": "disabled"})

    agent_id: str = body.get("agent_id", "unknown")
    event: str = body.get("event", "")
    if not event:
        return JSONResponse(status_code=400, content=error("missing_field", "event is required"))

    await obs.agent.log(
        agent_id=agent_id,
        event=event,
        detail=body.get("detail", ""),
        metadata=body.get("metadata"),
        tags=body.get("tags"),
    )
    return success({"written": True, "path": f"agents/{agent_id}/"})


# ── POST /obsidian/log/decision ───────────────────────────────────────────────

@router.post("/log/decision")
async def log_decision(body: dict[str, Any]):
    """
    Body: { decision, agent_id?, task_id?, reasoning?, outcome?, confidence?, links? }
    """
    obs = _obs()
    if obs is None:
        return success({"written": False, "reason": "disabled"})

    decision: str = body.get("decision", "")
    if not decision:
        return JSONResponse(status_code=400, content=error("missing_field", "decision is required"))

    await obs.decision.log(
        decision=decision,
        agent_id=body.get("agent_id"),
        task_id=body.get("task_id"),
        reasoning=body.get("reasoning", ""),
        outcome=body.get("outcome", "pending"),
        confidence=body.get("confidence"),
        links=body.get("links"),
    )
    return success({"written": True, "path": "swarm/decisions.md"})


# ── POST /obsidian/log/memory ─────────────────────────────────────────────────

@router.post("/log/memory")
async def log_memory(body: dict[str, Any]):
    """
    Body: { type: "short"|"long", content, source?, session_id?, category?, confidence?, source_agent? }
    """
    obs = _obs()
    if obs is None:
        return success({"written": False, "reason": "disabled"})

    mem_type: Literal["short", "long"] = body.get("type", "short")
    content: str = body.get("content", "")
    if not content:
        return JSONResponse(status_code=400, content=error("missing_field", "content is required"))

    if mem_type == "long":
        await obs.memory.log_long_term(
            fact=content,
            category=body.get("category", "general"),
            confidence=float(body.get("confidence", 1.0)),
            source_agent=body.get("source_agent"),
        )
        path = "memory/long_term.md"
    else:
        await obs.memory.log_short_term(
            content=content,
            source=body.get("source", "agent"),
            session_id=body.get("session_id"),
        )
        path = "memory/short_term.md"

    return success({"written": True, "path": path})


# ── POST /obsidian/log/task ───────────────────────────────────────────────────

@router.post("/log/task")
async def log_task(body: dict[str, Any]):
    """
    Body: { action: "start"|"complete", task_id, task?, agent_id?, success?, duration_ms?, summary?, error? }
    """
    obs = _obs()
    if obs is None:
        return success({"written": False, "reason": "disabled"})

    action: str = body.get("action", "start")
    task_id: str = body.get("task_id", "")
    if not task_id:
        return JSONResponse(status_code=400, content=error("missing_field", "task_id is required"))

    if action == "start":
        await obs.task.log_start(
            task_id=task_id,
            task=body.get("task", ""),
            agent_id=body.get("agent_id"),
            metadata=body.get("metadata"),
        )
    else:
        await obs.task.log_complete(
            task_id=task_id,
            success=body.get("success", True),
            duration_ms=body.get("duration_ms"),
            summary=body.get("summary", ""),
            error=body.get("error"),
        )

    from app.obsidian.writer import _today
    return success({"written": True, "path": f"tasks/{_today()}.md"})


# ── POST /obsidian/log/improvement ────────────────────────────────────────────

@router.post("/log/improvement")
async def log_improvement(body: dict[str, Any]):
    """
    Body: { type: "win"|"failure", prompt, outcome?, failure_reason?, model?, score?, agent_id?, retry_count? }
    """
    obs = _obs()
    if obs is None:
        return success({"written": False, "reason": "disabled"})

    imp_type: str = body.get("type", "win")
    prompt: str = body.get("prompt", "")
    if not prompt:
        return JSONResponse(status_code=400, content=error("missing_field", "prompt is required"))

    if imp_type == "win":
        await obs.improvement.log_win(
            prompt=prompt,
            outcome=body.get("outcome", ""),
            model=body.get("model", ""),
            score=body.get("score"),
            agent_id=body.get("agent_id"),
            tags=body.get("tags"),
        )
        path = "self_improvement/prompt_wins.md"
    else:
        await obs.improvement.log_failure(
            prompt=prompt,
            failure_reason=body.get("failure_reason", ""),
            model=body.get("model", ""),
            retry_count=int(body.get("retry_count", 0)),
            agent_id=body.get("agent_id"),
            tags=body.get("tags"),
        )
        path = "self_improvement/prompt_failures.md"

    return success({"written": True, "path": path})


# ── GET /obsidian/graph ───────────────────────────────────────────────────────

_WIKILINK_RE = re.compile(r"\[\[([^\]|]+)(?:\|[^\]]+)?\]\]")

@router.get("/graph")
async def get_graph():
    """
    Parse all vault .md files and return nodes + edges for graph visualisation.
    Compatible with Obsidian-style [[wikilink]] format.
    """
    obs = _obs()
    if obs is None:
        return error("obsidian_disabled", "Obsidian integration is disabled")

    vault = Path(obs.vault_root)
    nodes: list[dict] = []
    edges: list[dict] = []
    seen_nodes: set[str] = set()

    def node_id(path: str) -> str:
        return path.replace("/", ":").replace(".md", "")

    def node_type(path: str) -> str:
        parts = path.split("/")
        if parts[0] == "agents":
            return "agent"
        if parts[0] == "swarm":
            return "swarm"
        if parts[0] == "memory":
            return "memory"
        if parts[0] == "tasks":
            return "task"
        if parts[0] == "self_improvement":
            return "improvement"
        return "note"

    for f in sorted(vault.rglob("*.md")):
        rel = str(f.relative_to(vault))
        nid = node_id(rel)
        size = f.stat().st_size

        if nid not in seen_nodes:
            nodes.append({
                "id": nid,
                "label": f.stem,
                "path": rel,
                "type": node_type(rel),
                "size": size,
            })
            seen_nodes.add(nid)

        try:
            text = f.read_text(encoding="utf-8")
        except Exception:
            continue

        for match in _WIKILINK_RE.finditer(text):
            target_raw = match.group(1).strip()
            # Normalise: add .md if missing
            if not target_raw.endswith(".md"):
                target_raw += ".md"
            tid = node_id(target_raw)

            if tid not in seen_nodes:
                nodes.append({
                    "id": tid,
                    "label": Path(target_raw).stem,
                    "path": target_raw,
                    "type": node_type(target_raw),
                    "size": 0,
                })
                seen_nodes.add(tid)

            edges.append({"source": nid, "target": tid})

    return success({
        "nodes": nodes,
        "edges": edges,
        "node_count": len(nodes),
        "edge_count": len(edges),
    })
