from __future__ import annotations

import asyncio
import sys
import time

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.core.config import get_settings
from app.core.envelopes import error, success
from app.core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()

_ALLOWED_LANGUAGES = {"python", "shell"}


@router.post("/execution/run")
async def run_code(request: Request) -> dict:
    correlation_id = request.headers.get("x-correlation-id")
    settings = get_settings()

    if not settings.sandbox_enabled:
        return JSONResponse(
            status_code=503,
            content=error("execution_disabled", "Code execution sandbox is disabled", correlation_id=correlation_id),
        )

    try:
        body = await request.json()
    except Exception:
        return JSONResponse(
            status_code=400,
            content=error("invalid_request", "Request body must be valid JSON", correlation_id=correlation_id),
        )

    code: str = body.get("code", "").strip()
    language: str = (body.get("language") or "python").lower()
    timeout: int = min(int(body.get("timeout", settings.sandbox_timeout_seconds)), settings.sandbox_timeout_seconds)

    if not code:
        return JSONResponse(
            status_code=400,
            content=error("invalid_request", "code is required", correlation_id=correlation_id),
        )

    if language not in _ALLOWED_LANGUAGES:
        return JSONResponse(
            status_code=400,
            content=error(
                "invalid_language",
                f"Unsupported language '{language}'. Allowed: {sorted(_ALLOWED_LANGUAGES)}",
                correlation_id=correlation_id,
            ),
        )

    if language == "python":
        result = await _run_python(code, timeout, settings.sandbox_output_limit_bytes)
    else:
        result = await _run_shell(code, timeout, settings.sandbox_output_limit_bytes, settings.sandbox_network_disabled)

    return success(result, correlation_id)


@router.get("/execution/status")
async def execution_status(request: Request) -> dict:
    correlation_id = request.headers.get("x-correlation-id")
    settings = get_settings()
    return success(
        {
            "enabled": settings.sandbox_enabled,
            "languages": sorted(_ALLOWED_LANGUAGES),
            "timeoutSeconds": settings.sandbox_timeout_seconds,
            "networkDisabled": settings.sandbox_network_disabled,
            "outputLimitBytes": settings.sandbox_output_limit_bytes,
        },
        correlation_id,
    )


async def _run_python(code: str, timeout_s: int, output_limit: int) -> dict:
    """Execute Python in a subprocess with captured stdout/stderr."""
    start = time.perf_counter()
    try:
        proc = await asyncio.create_subprocess_exec(
            sys.executable, "-c", code,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout_bytes, stderr_bytes = await asyncio.wait_for(
                proc.communicate(), timeout=timeout_s
            )
        except asyncio.TimeoutError:
            proc.kill()
            await proc.communicate()
            return {
                "stdout": "",
                "stderr": f"Timeout: execution exceeded {timeout_s}s",
                "exitCode": -1,
                "durationMs": round((time.perf_counter() - start) * 1000),
                "timedOut": True,
                "language": "python",
            }
    except Exception as exc:
        return {
            "stdout": "",
            "stderr": str(exc),
            "exitCode": -1,
            "durationMs": round((time.perf_counter() - start) * 1000),
            "timedOut": False,
            "language": "python",
        }

    stdout = stdout_bytes.decode(errors="replace")[:output_limit]
    stderr = stderr_bytes.decode(errors="replace")[:output_limit]
    return {
        "stdout": stdout,
        "stderr": stderr,
        "exitCode": proc.returncode,
        "durationMs": round((time.perf_counter() - start) * 1000),
        "timedOut": False,
        "language": "python",
    }


async def _run_shell(code: str, timeout_s: int, output_limit: int, network_disabled: bool) -> dict:
    """Execute a shell command (bash) in a subprocess."""
    start = time.perf_counter()
    try:
        proc = await asyncio.create_subprocess_shell(
            code,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout_bytes, stderr_bytes = await asyncio.wait_for(
                proc.communicate(), timeout=timeout_s
            )
        except asyncio.TimeoutError:
            proc.kill()
            await proc.communicate()
            return {
                "stdout": "",
                "stderr": f"Timeout: execution exceeded {timeout_s}s",
                "exitCode": -1,
                "durationMs": round((time.perf_counter() - start) * 1000),
                "timedOut": True,
                "language": "shell",
            }
    except Exception as exc:
        return {
            "stdout": "",
            "stderr": str(exc),
            "exitCode": -1,
            "durationMs": round((time.perf_counter() - start) * 1000),
            "timedOut": False,
            "language": "shell",
        }

    stdout = stdout_bytes.decode(errors="replace")[:output_limit]
    stderr = stderr_bytes.decode(errors="replace")[:output_limit]
    return {
        "stdout": stdout,
        "stderr": stderr,
        "exitCode": proc.returncode,
        "durationMs": round((time.perf_counter() - start) * 1000),
        "timedOut": False,
        "language": "shell",
    }
