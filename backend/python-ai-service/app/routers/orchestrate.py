"""POST /orchestrate/run — SSE endpoint for multi-agent orchestration.

Request body:
  {
    "task":       "Add type hints to all Python files",
    "file_tree":  "src/main.py\nsrc/utils.py\n...",   // optional
    "history":    [{"role":"user","content":"..."}],   // optional
    "repo_root":  "/workspace/myproject",              // optional
    "max_files":  10                                   // optional
  }

Response: text/event-stream
  event: status       → {"message":"...", "phase":"..."}
  event: plan         → {"steps":[...], "summary":"..."}
  event: agent_result → AgentResult.to_dict()
  event: review       → ReviewerAgent data dict
  event: done         → {"total_steps":N, "completed":N, "files_modified":[...]}
  event: error        → {"message":"..."}
"""
from __future__ import annotations

import json
from typing import AsyncIterator

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.agents.orchestrator import Orchestrator
from app.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/orchestrate", tags=["orchestrate"])


class OrchestrateRequest(BaseModel):
    task: str
    file_tree: str = ""
    history: list[dict] = []
    repo_root: str = "."
    max_files: int = 10


def _sse_line(event_type: str, data: dict) -> str:
    payload = json.dumps(data, ensure_ascii=False)
    return f"event: {event_type}\ndata: {payload}\n\n"


async def _stream(req: OrchestrateRequest) -> AsyncIterator[str]:
    try:
        orch = Orchestrator(repo_root=req.repo_root)
        async for event in orch.run(
            task=req.task,
            file_tree=req.file_tree,
            history=req.history,
            max_files=req.max_files,
        ):
            event_type = event.get("event", "data")
            data       = event.get("data", {})
            yield _sse_line(event_type, data)
    except Exception as exc:
        logger.error("orchestrate_stream_error", error=str(exc))
        yield _sse_line("error", {"message": str(exc)})
    finally:
        yield _sse_line("close", {})


@router.post("/run")
async def orchestrate_run(req: OrchestrateRequest):
    """Stream multi-agent orchestration results as SSE."""
    return StreamingResponse(
        _stream(req),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/models")
async def list_free_models():
    """List all free OpenRouter models used by the agent pool."""
    from app.agents.free_model_pool import FreeModelPool, AgentRole
    return {
        "openrouter_available": FreeModelPool.openrouter_available(),
        "models": FreeModelPool.all_models(),
        "role_map": {
            role.value: [
                FreeModelPool.get_model(role, 0),
                FreeModelPool.get_model(role, 1),
            ]
            for role in AgentRole
        },
    }


@router.get("/nim-models")
async def list_nim_models():
    """List all NVIDIA NIM free endpoint models + agent role mapping."""
    from app.agents.nim_model_pool import NimModelPool, NIM_FREE_MODELS, _NIM_ROLE_MAP
    from app.agents.free_model_pool import AgentRole
    return {
        "nim_available": NimModelPool.available(),
        "base_url": NimModelPool.get_base_url(),
        "models": [
            {
                "model_id": m.model_id,
                "slug": m.slug,
                "name": m.name,
                "context_length": m.context_length,
                "use_cases": m.use_cases,
                "publisher": m.publisher,
                "free": m.free,
                "build_url": NimModelPool.nim_build_url(m.slug),
            }
            for m in NIM_FREE_MODELS
        ],
        "role_map": {
            role.value: _NIM_ROLE_MAP.get(role, [])
            for role in AgentRole
        },
    }
