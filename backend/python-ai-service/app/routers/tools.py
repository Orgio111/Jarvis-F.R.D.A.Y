from __future__ import annotations

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

    result = await _dispatch_tool(tool_id, body)
    return success({"toolId": tool_id, "result": result}, correlation_id)


async def _dispatch_tool(tool_id: str, params: dict) -> dict:
    if tool_id == "code_execute":
        from app.routers.execution import _run_python, _run_shell
        language = (params.get("language") or "python").lower()
        code = params.get("code", "")
        timeout = int(params.get("timeout", 30))
        if language == "shell":
            return await _run_shell(code, timeout, 200_000, False)
        return await _run_python(code, timeout, 200_000)

    if tool_id == "memory_search":
        from app.routers.memory import _search_memory
        from app.core.config import get_settings
        settings = get_settings()
        return {"results": await _search_memory(params.get("query", ""), int(params.get("topK", 5)), settings)}

    if tool_id == "memory_store":
        from app.routers.memory import _store_memory
        from app.core.config import get_settings
        settings = get_settings()
        return await _store_memory(params.get("content", ""), params.get("metadata", {}), settings)

    if tool_id == "web_search":
        return {"results": [], "note": "Web search not yet connected to a provider"}

    return {"note": f"Tool '{tool_id}' dispatched but no executor is registered"}
