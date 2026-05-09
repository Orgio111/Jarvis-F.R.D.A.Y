from __future__ import annotations

import asyncio
import shlex
from uuid import uuid4

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.core.config import get_settings
from app.core.envelopes import error, success
from app.core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()

# Approval queue — actions requiring human sign-off before execution
_pending_approvals: dict[str, dict] = {}

# Allowlist of safe, read-only system commands that don't need approval
_SAFE_NO_APPROVAL = {
    "get_system_info",
    "list_processes",
    "disk_usage",
    "memory_info",
    "network_interfaces",
}

_BUILTIN_ACTIONS: list[dict] = [
    {
        "id": "get_system_info",
        "name": "System Info",
        "description": "Return OS, CPU, and memory info",
        "category": "system",
        "requiresApproval": False,
        "enabled": True,
    },
    {
        "id": "list_processes",
        "name": "List Processes",
        "description": "List top running processes",
        "category": "system",
        "requiresApproval": False,
        "enabled": True,
    },
    {
        "id": "disk_usage",
        "name": "Disk Usage",
        "description": "Show disk space usage",
        "category": "system",
        "requiresApproval": False,
        "enabled": True,
    },
    {
        "id": "open_browser",
        "name": "Open Browser",
        "description": "Open a URL in the default browser",
        "category": "ui",
        "requiresApproval": True,
        "enabled": True,
        "parameters": [{"name": "url", "type": "string", "required": True}],
    },
    {
        "id": "run_shell",
        "name": "Run Shell Command",
        "description": "Execute an arbitrary shell command (requires approval)",
        "category": "shell",
        "requiresApproval": True,
        "enabled": True,
        "parameters": [{"name": "command", "type": "string", "required": True}],
    },
]


@router.get("/local-actions")
async def list_actions(request: Request) -> dict:
    correlation_id = request.headers.get("x-correlation-id")
    settings = get_settings()
    if not settings.local_pc_control_enabled:
        return success({"actions": [], "total": 0, "enabled": False}, correlation_id)
    return success(
        {
            "actions": _BUILTIN_ACTIONS,
            "total": len(_BUILTIN_ACTIONS),
            "enabled": True,
            "requireApproval": settings.local_admin_actions_require_approval,
        },
        correlation_id,
    )


@router.get("/local-actions/pending")
async def list_pending(request: Request) -> dict:
    correlation_id = request.headers.get("x-correlation-id")
    return success(
        {"pending": list(_pending_approvals.values()), "total": len(_pending_approvals)},
        correlation_id,
    )


@router.post("/local-actions/{action_id}/execute")
async def execute_action(action_id: str, request: Request) -> dict:
    correlation_id = request.headers.get("x-correlation-id")
    settings = get_settings()

    if not settings.local_pc_control_enabled:
        return JSONResponse(
            status_code=503,
            content=error("local_control_disabled", "Local PC control is disabled", correlation_id=correlation_id),
        )

    action = next((a for a in _BUILTIN_ACTIONS if a["id"] == action_id), None)
    if not action:
        return JSONResponse(
            status_code=404,
            content=error("not_found", f"Action '{action_id}' not found", correlation_id=correlation_id),
        )

    try:
        body = await request.json()
    except Exception:
        body = {}

    requires_approval = action.get("requiresApproval", True) and settings.local_admin_actions_require_approval

    if requires_approval:
        approval_id = f"apr_{uuid4().hex[:8]}"
        _pending_approvals[approval_id] = {
            "id": approval_id,
            "actionId": action_id,
            "actionName": action["name"],
            "params": body,
            "status": "pending",
        }
        return success(
            {"queued": True, "approvalId": approval_id, "message": "Action queued for human approval"},
            correlation_id,
        )

    result = await _run_action(action_id, body)
    return success(result, correlation_id)


@router.post("/local-actions/approvals/{approval_id}/approve")
async def approve_action(approval_id: str, request: Request) -> dict:
    correlation_id = request.headers.get("x-correlation-id")
    entry = _pending_approvals.pop(approval_id, None)
    if not entry:
        return JSONResponse(
            status_code=404,
            content=error("not_found", f"Approval '{approval_id}' not found", correlation_id=correlation_id),
        )
    result = await _run_action(entry["actionId"], entry.get("params", {}))
    return success({"executed": True, "approvalId": approval_id, "result": result}, correlation_id)


@router.post("/local-actions/approvals/{approval_id}/deny")
async def deny_action(approval_id: str, request: Request) -> dict:
    correlation_id = request.headers.get("x-correlation-id")
    entry = _pending_approvals.pop(approval_id, None)
    if not entry:
        return JSONResponse(
            status_code=404,
            content=error("not_found", f"Approval '{approval_id}' not found", correlation_id=correlation_id),
        )
    return success({"denied": True, "approvalId": approval_id}, correlation_id)


# ─── Action executors ──────────────────────────────────────────────────────────

async def _run_action(action_id: str, params: dict) -> dict:
    if action_id == "get_system_info":
        return await _run_shell_cmd("uname -a && hostname && uptime")
    if action_id == "list_processes":
        return await _run_shell_cmd("ps aux --sort=-%cpu | head -20")
    if action_id == "disk_usage":
        return await _run_shell_cmd("df -h")
    if action_id == "open_browser":
        url = params.get("url", "")
        if not url.startswith(("http://", "https://")):
            return {"error": "Invalid URL — must start with http:// or https://"}
        import subprocess
        try:
            subprocess.Popen(["xdg-open", url])
            return {"opened": True, "url": url}
        except Exception as exc:
            return {"error": str(exc)}
    if action_id == "run_shell":
        cmd = params.get("command", "").strip()
        if not cmd:
            return {"error": "command is required"}
        return await _run_shell_cmd(cmd)
    return {"note": f"No executor for action '{action_id}'"}


async def _run_shell_cmd(cmd: str) -> dict:
    try:
        proc = await asyncio.create_subprocess_shell(
            cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout_b, stderr_b = await asyncio.wait_for(proc.communicate(), timeout=15)
        return {
            "stdout": stdout_b.decode(errors="replace")[:10_000],
            "stderr": stderr_b.decode(errors="replace")[:2_000],
            "exitCode": proc.returncode,
        }
    except asyncio.TimeoutError:
        return {"error": "Command timed out after 15s"}
    except Exception as exc:
        return {"error": str(exc)}
