from __future__ import annotations

import json
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from app.core.config import get_settings
from app.core.envelopes import error, new_event, success
from app.core.errors import ProviderUnavailableError
from app.core.logging import get_logger
from app.providers.router import ProviderRouter

logger = get_logger(__name__)
router = APIRouter()


@router.post("/chat/completions")
async def chat_completions(request: Request) -> Any:
    correlation_id = request.headers.get("x-correlation-id", str(uuid4()))
    session_id = request.headers.get("x-session-id")
    req_id = request.headers.get("x-request-id")

    try:
        body = await request.json()
    except Exception:
        return _json_error(400, "invalid_request", "Request body must be valid JSON", correlation_id)

    messages = body.get("messages")
    if not messages or not isinstance(messages, list):
        return _json_error(400, "invalid_request", "messages is required and must be a list", correlation_id)

    settings = get_settings()
    model_id: str = body.get("model") or settings.default_chat_model or ""
    max_tokens: int | None = body.get("max_tokens") or settings.ai_max_tokens or None
    stream: bool = body.get("stream", True)

    try:
        pr = ProviderRouter.get()
        provider = pr.get_active_provider()
        if provider is None:
            return _json_error(503, "provider_unavailable", "No AI provider is available", correlation_id)
    except Exception as exc:
        logger.error("chat_provider_lookup_failed", error=str(exc))
        return _json_error(503, "provider_unavailable", str(exc), correlation_id)

    if not model_id:
        try:
            models = await provider.list_models()
            model_id = models[0]["id"] if models else ""
        except Exception:
            pass

    if not model_id:
        return _json_error(400, "model_required", "No model specified and no default model available", correlation_id)

    if stream:
        return StreamingResponse(
            _stream_events(provider, messages, model_id, max_tokens, correlation_id, session_id, req_id),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
            },
        )

    try:
        result = await provider.chat(messages, model_id, max_tokens)
        content = _extract_content(result)
        return success(
            {
                "messageId": f"msg_{uuid4()}",
                "role": "assistant",
                "content": content,
                "model": model_id,
                "providerId": provider.provider_id,
                "finishReason": result.get("choices", [{}])[0].get("finish_reason", "stop"),
                "usage": result.get("usage"),
            },
            correlation_id,
        )
    except Exception as exc:
        logger.error("chat_completion_failed", error=str(exc))
        return _json_error(500, "completion_error", str(exc), correlation_id)


async def _stream_events(
    provider: Any,
    messages: list[dict],
    model_id: str,
    max_tokens: int | None,
    correlation_id: str,
    session_id: str | None,
    req_id: str | None,
) -> Any:
    message_id = f"msg_{uuid4()}"

    # start event
    yield _sse(new_event(
        "CHAT_STREAM_START",
        {"messageId": message_id, "model": model_id, "providerId": provider.provider_id},
        correlation_id, req_id, session_id,
    ))

    full_content: list[str] = []
    try:
        async for raw_chunk in provider.stream_chat(messages, model_id, max_tokens):
            try:
                chunk_data = json.loads(raw_chunk)
            except Exception:
                continue
            delta = chunk_data.get("choices", [{}])[0].get("delta", {})
            token = delta.get("content", "")
            if token:
                full_content.append(token)
                yield _sse(new_event(
                    "CHAT_STREAM_TOKEN",
                    {"messageId": message_id, "token": token},
                    correlation_id, req_id, session_id,
                ))
    except Exception as exc:
        logger.error("chat_stream_error", error=str(exc))
        yield _sse(new_event(
            "CHAT_STREAM_ERROR",
            {"messageId": message_id, "error": str(exc)},
            correlation_id, req_id, session_id,
        ))
        yield "data: [DONE]\n\n"
        return

    yield _sse(new_event(
        "CHAT_STREAM_END",
        {
            "messageId": message_id,
            "content": "".join(full_content),
            "model": model_id,
            "providerId": provider.provider_id,
        },
        correlation_id, req_id, session_id,
    ))
    yield "data: [DONE]\n\n"


def _sse(event: dict) -> str:
    return f"data: {json.dumps(event)}\n\n"


def _json_error(status: int, code: str, message: str, correlation_id: str) -> Any:
    from fastapi.responses import JSONResponse
    return JSONResponse(
        status_code=status,
        content=error(code, message, correlation_id=correlation_id),
    )


def _extract_content(result: dict) -> str:
    try:
        return result["choices"][0]["message"]["content"] or ""
    except (KeyError, IndexError):
        return ""
