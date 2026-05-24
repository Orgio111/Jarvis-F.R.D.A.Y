"""FastAPI router for Device Agent — browser automation + UI analysis."""

from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.device_agent.engine import get_agent
from app.core.envelopes import error, success

router = APIRouter(prefix="/device-agent")


@router.post("/browser/navigate")
async def browser_navigate(request: Request) -> dict:
    correlation_id = request.headers.get("x-correlation-id")
    try:
        body = await request.json()
    except Exception:
        return JSONResponse(status_code=400, content=error("invalid_request", "Invalid JSON", correlation_id))

    url = (body.get("url") or "").strip()
    if not url:
        return JSONResponse(status_code=400, content=error("invalid_request", "url is required", correlation_id))

    agent = get_agent()
    result = await agent.navigate(url)
    return success(result, correlation_id)


@router.post("/browser/click")
async def browser_click(request: Request) -> dict:
    correlation_id = request.headers.get("x-correlation-id")
    try:
        body = await request.json()
    except Exception:
        return JSONResponse(status_code=400, content=error("invalid_request", "Invalid JSON", correlation_id))

    agent = get_agent()
    result = await agent.click(selector=body.get("selector", ""))
    return success(result, correlation_id)


@router.post("/browser/type")
async def browser_type(request: Request) -> dict:
    correlation_id = request.headers.get("x-correlation-id")
    try:
        body = await request.json()
    except Exception:
        return JSONResponse(status_code=400, content=error("invalid_request", "Invalid JSON", correlation_id))

    agent = get_agent()
    result = await agent.type_text(
        selector=body.get("selector", ""),
        text=body.get("text", ""),
    )
    return success(result, correlation_id)


@router.post("/browser/screenshot")
async def browser_screenshot(request: Request) -> dict:
    correlation_id = request.headers.get("x-correlation-id")
    agent = get_agent()
    result = await agent.screenshot()
    return success(result, correlation_id)


@router.get("/browser/ui")
async def browser_ui_analysis(request: Request) -> dict:
    correlation_id = request.headers.get("x-correlation-id")
    agent = get_agent()
    result = await agent.analyze_ui()
    return success(result, correlation_id)


@router.get("/history")
async def device_history(request: Request) -> dict:
    correlation_id = request.headers.get("x-correlation-id")
    agent = get_agent()
    history = await agent.get_history()
    return success({"actions": history, "total": len(history)}, correlation_id)


@router.post("/close")
async def close_device_agent(request: Request) -> dict:
    correlation_id = request.headers.get("x-correlation-id")
    from app.device_agent.engine import close_agent
    await close_agent()
    return success({"closed": True}, correlation_id)
