from __future__ import annotations

import asyncio
import json
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse

from app.core.config import get_settings
from app.core.envelopes import error, new_event, success
from app.core.logging import get_logger
from app.db.database import get_db
from app.providers.router import ProviderRouter

logger = get_logger(__name__)
router = APIRouter()


async def _enrich_messages_with_memory(
    db,
    messages: list[dict],
    session_id: str | None,
    user_id: str,
) -> list[dict]:
    """Prepend relevant long-term memories + user profile to the system prompt."""
    try:
        from app.services import memory_service, profile_service

        # Pull relevant context for the last user message
        user_msg = next(
            (m.get("content", "") for m in reversed(messages) if m.get("role") == "user"),
            "",
        )

        memories: list[dict] = []
        if user_msg:
            memories = await memory_service.search(db, query=user_msg, top_k=3)

        profile_summary = await profile_service.context_summary(db, user_id)

        extra_context_parts: list[str] = []
        if profile_summary:
            extra_context_parts.append(f"[User profile]\n{profile_summary}")
        if memories:
            mem_text = "\n".join(f"- {m['content'][:200]}" for m in memories)
            extra_context_parts.append(f"[Relevant memory]\n{mem_text}")

        if not extra_context_parts:
            return messages

        extra_block = "\n\n".join(extra_context_parts)
        enriched = list(messages)

        # Append to existing system message, or insert one
        if enriched and enriched[0].get("role") == "system":
            enriched[0] = {
                **enriched[0],
                "content": enriched[0]["content"] + "\n\n" + extra_block,
            }
        else:
            enriched.insert(0, {"role": "system", "content": extra_block})

        return enriched
    except Exception as exc:
        logger.debug("memory_enrichment_skipped", reason=str(exc))
        return messages


async def _post_turn_update(db, user_msg: str, assistant_msg: str, session_id: str | None, user_id: str) -> None:
    """Background: store turn in memory + update user profile."""
    try:
        from app.services import memory_service, profile_service

        await memory_service.store(
            db,
            content=f"User: {user_msg}\nAssistant: {assistant_msg}",
            metadata={"session_id": session_id or "", "role": "turn", "user_id": user_id},
            memory_type="episodic",
            importance=0.5,
        )
        await profile_service.update_from_conversation(db, user_msg, assistant_msg, user_id)
    except Exception as exc:
        logger.debug("post_turn_update_failed", reason=str(exc))


@router.post("/chat/completions")
async def chat_completions(request: Request, db=Depends(get_db)) -> Any:
    correlation_id = request.headers.get("x-correlation-id", str(uuid4()))
    session_id = request.headers.get("x-session-id")
    req_id = request.headers.get("x-request-id")
    user_id = request.headers.get("x-user-id", "default")

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

    # Enrich messages with long-term memory + user profile
    messages = await _enrich_messages_with_memory(db, messages, session_id, user_id)

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
            _stream_events(provider, messages, model_id, max_tokens, correlation_id, session_id, req_id, db, user_id),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
            },
        )

    # Extract original user message before enrichment for memory storage
    user_msg = next(
        (m.get("content", "") for m in reversed(messages) if m.get("role") == "user"),
        "",
    )

    try:
        result = await provider.chat(messages, model_id, max_tokens)
        content = _extract_content(result)

        # Background: store turn + update profile
        asyncio.ensure_future(_post_turn_update(db, user_msg, content, session_id, user_id))

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
    db: Any = None,
    user_id: str = "default",
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

    assembled = "".join(full_content)
    yield _sse(new_event(
        "CHAT_STREAM_END",
        {
            "messageId": message_id,
            "content": assembled,
            "model": model_id,
            "providerId": provider.provider_id,
        },
        correlation_id, req_id, session_id,
    ))
    yield "data: [DONE]\n\n"

    # Background: store turn in memory + update profile
    if db is not None and assembled:
        user_msg = next(
            (m.get("content", "") for m in reversed(messages) if m.get("role") == "user"),
            "",
        )
        asyncio.ensure_future(_post_turn_update(db, user_msg, assembled, session_id, user_id))


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
