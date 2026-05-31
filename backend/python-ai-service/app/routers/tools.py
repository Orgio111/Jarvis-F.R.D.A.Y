from __future__ import annotations

import asyncio

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.core.envelopes import error, success
from app.core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()

# ─── Built-in tool registry ────────────────────────────────────────────────────

_BUILTIN_TOOLS: list[dict] = [
    {
        "id": "web_search",
        "name": "Web Search",
        "description": "Search the web using a query string",
        "category": "search",
        "enabled": True,
        "parameters": [
            {"name": "query", "type": "string", "required": True, "description": "Search query"},
            {"name": "maxResults", "type": "integer", "required": False, "description": "Max results (default 5)"},
        ],
    },
    {
        "id": "code_execute",
        "name": "Code Execute",
        "description": "Execute Python or shell code in a sandboxed environment",
        "category": "execution",
        "enabled": True,
        "parameters": [
            {"name": "code", "type": "string", "required": True, "description": "Code to execute"},
            {"name": "language", "type": "string", "required": False, "description": "Language: python or shell"},
            {"name": "timeout", "type": "integer", "required": False, "description": "Timeout in seconds"},
        ],
    },
    {
        "id": "memory_search",
        "name": "Memory Search",
        "description": "Search long-term memory for relevant context",
        "category": "memory",
        "enabled": True,
        "parameters": [
            {"name": "query", "type": "string", "required": True, "description": "Search query"},
            {"name": "topK", "type": "integer", "required": False, "description": "Number of results"},
        ],
    },
    {
        "id": "memory_store",
        "name": "Memory Store",
        "description": "Store information in long-term memory",
        "category": "memory",
        "enabled": True,
        "parameters": [
            {"name": "content", "type": "string", "required": True, "description": "Content to store"},
            {"name": "metadata", "type": "object", "required": False, "description": "Optional metadata"},
        ],
    },
    {
        "id": "file_read",
        "name": "File Read",
        "description": "Read a local file (with path restrictions)",
        "category": "local",
        "enabled": False,
        "parameters": [
            {"name": "path", "type": "string", "required": True, "description": "File path"},
        ],
    },
    {
        "id": "file_write",
        "name": "File Write",
        "description": "Write content to a local file",
        "category": "local",
        "enabled": False,
        "parameters": [
            {"name": "path", "type": "string", "required": True, "description": "File path"},
            {"name": "content", "type": "string", "required": True, "description": "Content to write"},
        ],
    },
]


@router.get("/tools")
async def list_tools(request: Request) -> dict:
    correlation_id = request.headers.get("x-correlation-id")
    return success(
        {
            "tools": _BUILTIN_TOOLS,
            "total": len(_BUILTIN_TOOLS),
            "enabled": sum(1 for t in _BUILTIN_TOOLS if t["enabled"]),
        },
        correlation_id,
    )


@router.post("/tools/{tool_id}/execute")
async def execute_tool(tool_id: str, request: Request) -> dict:
    correlation_id = request.headers.get("x-correlation-id")

    tool = next((t for t in _BUILTIN_TOOLS if t["id"] == tool_id), None)
    if tool is None:
        return JSONResponse(
            status_code=404,
            content=error("not_found", f"Tool '{tool_id}' not found", correlation_id=correlation_id),
        )
    if not tool["enabled"]:
        return JSONResponse(
            status_code=503,
            content=error("tool_disabled", f"Tool '{tool_id}' is disabled", correlation_id=correlation_id),
        )

    try:
        body = await request.json()
    except Exception:
        return JSONResponse(
            status_code=400,
            content=error("invalid_request", "Request body must be valid JSON", correlation_id=correlation_id),
        )

    # Check skill crystallization cache first — skip re-execution if we have a good match
    from app.services.skill_service import find_similar_skill
    cache_query = f"{tool_id}: {body}"
    cached_skill = await find_similar_skill(cache_query)
    if cached_skill and cached_skill.get("score", 0) >= 0.85:
        logger.info("tool_cache_hit", tool_id=tool_id, score=cached_skill["score"])
        return success(
            {
                "toolId": tool_id,
                "result": {
                    "output": cached_skill["metadata"].get("output_preview", ""),
                    "from_cache": True,
                    "cache_score": cached_skill["score"],
                    "note": "Result from crystallized skill cache",
                },
            },
            correlation_id,
        )

    result = await _dispatch_tool(tool_id, body)

    # Crystallize if result is high quality
    if result.get("success", False) or (result.get("output") and not result.get("error")):
        from app.services.skill_service import assess_quality, crystallize
        score = assess_quality(result)
        if score >= 0.7:
            asyncio.ensure_future(crystallize(tool_id, body, result, score))
            result["crystallized"] = True
            result["qualityScore"] = score

    return success({"toolId": tool_id, "result": result}, correlation_id)


async def _dispatch_tool(tool_id: str, params: dict) -> dict:
    if tool_id == "code_execute":
        from app.routers.execution import _run_python, _run_shell
        language = (params.get("language") or "python").lower()
        code = params.get("code", "")
        timeout = int(params.get("timeout", 30))
        if language == "shell":
            raw = await _run_shell(code, timeout, 200_000, False)
        else:
            raw = await _run_python(code, timeout, 200_000)
        # Normalise to {success, output} for crystallization pipeline
        success_flag = raw.get("exitCode", 1) == 0 and not raw.get("timedOut", False)
        output_text = raw.get("stdout", "") or raw.get("output", "")
        return {
            **raw,
            "success": success_flag,
            "output": output_text,
            "error": raw.get("stderr") if raw.get("stderr") else None,
        }

    if tool_id == "memory_search":
        from app.routers.memory import _search_memory
        from app.core.config import get_settings
        settings = get_settings()
        results = await _search_memory(params.get("query", ""), int(params.get("topK", 5)), settings)
        return {"results": results, "success": True, "output": f"Found {len(results)} memory entries"}

    if tool_id == "memory_store":
        from app.routers.memory import _store_memory
        from app.core.config import get_settings
        settings = get_settings()
        raw = await _store_memory(params.get("content", ""), params.get("metadata", {}), settings)
        return {**raw, "success": True, "output": f"Stored memory entry id={raw.get('id')}"}

    if tool_id == "web_search":
        return {"results": [], "success": False, "output": "", "note": "Web search not yet connected to a provider"}

    return {"note": f"Tool '{tool_id}' dispatched but no executor is registered", "success": False, "output": ""}
