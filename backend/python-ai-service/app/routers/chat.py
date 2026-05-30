from __future__ import annotations

import asyncio
import json
import time
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse

from app.core.config import get_settings
from app.core.envelopes import error, new_event, success
from app.core.logging import get_logger
from app.core.model_modes import ALL_MODES, _EMBEDDING_KEYWORDS, resolve_mode
from app.core.persona import inject_system_prompt
from app.db.database import get_db
from app.providers.router import ProviderRouter

logger = get_logger(__name__)
router = APIRouter()

# ── Model resolution cache ────────────────────────────────────────────────────
# Resolved model IDs are cached per mode for 60 s to avoid /models roundtrips.
_model_cache: dict[str, tuple[str, float]] = {}
_MODEL_CACHE_TTL = 60.0


def _get_cached_model(mode: str) -> str | None:
    entry = _model_cache.get(mode)
    if entry and (time.monotonic() - entry[1]) < _MODEL_CACHE_TTL:
        return entry[0]
    return None


def _set_cached_model(mode: str, model_id: str) -> None:
    _model_cache[mode] = (model_id, time.monotonic())


# ── Memory enrichment (parallel + timeout) ───────────────────────────────────

_MEMORY_TIMEOUT = 1.5  # hard cap — never blocks the chat path


async def _enrich_messages_with_memory(
    db,
    messages: list[dict],
    session_id: str | None,
    user_id: str,
) -> list[dict]:
    """Parallel memory search + profile fetch, capped at _MEMORY_TIMEOUT.

    Returns original messages on timeout or any error — chat path never blocked.
    """
    try:
        from app.services import memory_service, profile_service

        user_msg = next(
            (m.get("content", "") for m in reversed(messages) if m.get("role") == "user"),
            "",
        )

        async def _search() -> list[dict]:
            if not user_msg:
                return []
            return await memory_service.search(db, query=user_msg, top_k=3)

        async def _profile() -> str:
            return await profile_service.context_summary(db, user_id)

        memories, profile_summary = await asyncio.wait_for(
            asyncio.gather(_search(), _profile(), return_exceptions=True),
            timeout=_MEMORY_TIMEOUT,
        )

        if isinstance(memories, BaseException):
            memories = []
        if isinstance(profile_summary, BaseException):
            profile_summary = ""

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

        if enriched and enriched[0].get("role") == "system":
            enriched[0] = {
                **enriched[0],
                "content": enriched[0]["content"] + "\n\n" + extra_block,
            }
        else:
            enriched.insert(0, {"role": "system", "content": extra_block})

        return enriched
    except asyncio.TimeoutError:
        logger.debug("memory_enrichment_timeout", budget_s=_MEMORY_TIMEOUT)
        return messages
    except Exception as exc:
        logger.debug("memory_enrichment_skipped", reason=str(exc))
        return messages


async def _post_turn_update(
    db, user_msg: str, assistant_msg: str, session_id: str | None, user_id: str
) -> None:
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


# ── Smart mode selection ──────────────────────────────────────────────────────

def _smart_mode(user_msg: str, requested_mode: str, settings: Any) -> str:
    """Use SmartRouter to pick fast/smart/deep/coding based on task complexity.

    Falls back to requested_mode on any error — never raises.
    """
    if requested_mode and requested_mode != "fast":
        # Explicit non-default mode from caller — respect it
        return requested_mode
    try:
        from app.brain.smart_router import SmartRouter
        sr = SmartRouter.get()
        result = sr.analyze_task(user_msg)
        recommended = result.get("recommendedMode", requested_mode)
        logger.debug(
            "smart_router_decision",
            complexity=result.get("complexity"),
            mode=recommended,
        )
        return recommended
    except Exception:
        return requested_mode


# ── Model resolution helper (with cache) ─────────────────────────────────────

async def _resolve_model_id(
    mode: str,
    settings: Any,
    pr: "ProviderRouter",
    providers: list[Any],
) -> str:
    """Best model_id for *mode*, with 60 s in-process cache to skip /models calls."""

    # 1. Config override — no network call
    override_key = f"model_mode_{mode}_model_override"
    override_model = getattr(settings, override_key, None) or ""
    if override_model:
        logger.info("mode_override_used", mode=mode, model=override_model)
        return override_model

    # 2. Cache hit
    cached = _get_cached_model(mode)
    if cached:
        logger.debug("model_cache_hit", mode=mode, model=cached)
        return cached

    # 3. Live resolution across all providers
    model_id = ""
    try:
        all_models = await pr.get_all_models()
        overrides = {
            m: getattr(settings, f"model_mode_{m}_model_override", None) or ""
            for m in ALL_MODES
        }
        resolution = resolve_mode(mode, all_models, overrides=overrides)
        if resolution:
            model_id = resolution.modelId
            logger.info("mode_resolved", mode=mode, model=model_id, provider=resolution.providerId)
    except Exception as exc:
        logger.debug("mode_resolution_failed", error=str(exc))

    # 4. Fallback: first chat model from first reachable provider
    if not model_id:
        for p in providers:
            try:
                models = await p.list_models()
                chat_models = [m for m in models if not _is_embedding_model(m["id"])]
                if chat_models:
                    model_id = chat_models[0]["id"]
                    break
            except Exception:
                continue

    if model_id:
        _set_cached_model(mode, model_id)

    return model_id


# ── Main endpoint ─────────────────────────────────────────────────────────────

@router.post("/chat/completions")
async def chat_completions(request: Request, db=Depends(get_db)) -> Any:
    t0 = time.monotonic()

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

    model_id: str = body.get("model") or ""
    mode: str = body.get("mode") or settings.default_chat_mode or "fast"
    max_tokens: int | None = body.get("max_tokens") or settings.ai_max_tokens or None
    stream: bool = body.get("stream", True)

    if mode not in ALL_MODES:
        mode = "fast"

    # SmartRouter: pick mode based on task complexity (fast only when mode == "fast")
    user_msg_raw = next(
        (m.get("content", "") for m in reversed(messages) if m.get("role") == "user"),
        "",
    )
    mode = _smart_mode(user_msg_raw, mode, settings)

    try:
        pr = ProviderRouter.get()
        providers = pr.get_providers_in_priority_order()
        if not providers:
            return _json_error(503, "provider_unavailable", "No AI provider is available", correlation_id)
    except Exception as exc:
        logger.error("chat_provider_lookup_failed", error=str(exc))
        return _json_error(503, "provider_unavailable", str(exc), correlation_id)

    # ── Semantic cache check (before memory enrich — uses raw messages) ───────
    from app.cache.semantic_cache import SemanticCache
    cache = SemanticCache.get()
    if cache and not model_id:
        # Resolve model first (needed for exact cache key) — use cache or quick override
        quick_model = (
            getattr(settings, f"model_mode_{mode}_model_override", None)
            or _get_cached_model(mode)
            or ""
        )
        if quick_model:
            cached_resp = await cache.get(messages, quick_model)
            if cached_resp is not None:
                logger.info("cache_hit_response", latency_ms=round((time.monotonic() - t0) * 1000))
                if stream:
                    # Stream the cached response as normal tokens for client compat
                    return StreamingResponse(
                        _stream_cached(cached_resp, quick_model, providers[0].provider_id if providers else "cache",
                                       correlation_id, session_id, req_id),
                        media_type="text/event-stream",
                        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
                    )
                return success(
                    {
                        "messageId": f"msg_{uuid4()}",
                        "role": "assistant",
                        "content": cached_resp,
                        "model": quick_model,
                        "providerId": "cache",
                        "finishReason": "stop",
                        "usage": None,
                        "cached": True,
                    },
                    correlation_id,
                )

    # ── Parallel: memory enrich + model resolve ───────────────────────────────
    enrich_task = asyncio.create_task(
        _enrich_messages_with_memory(db, messages, session_id, user_id)
    )
    resolve_task: asyncio.Task | None = None
    if not model_id:
        resolve_task = asyncio.create_task(
            _resolve_model_id(mode, settings, pr, providers)
        )

    messages = await enrich_task

    if resolve_task is not None:
        model_id = await resolve_task

    # ── IntentRouter: check for skill triggers BEFORE LLM ────────────────────
    try:
        from app.agents.intent_router import IntentRouter
        from app.services import skill_service as _svc
        _ir = IntentRouter(db)
        _skill_match = await _ir.match(user_msg_raw)
        if _skill_match:
            logger.info(
                "intent_router_skill_dispatch",
                skill_id=_skill_match["skill_id"],
                name=_skill_match["name"],
            )
            _skill_result = await _svc.execute(db, _skill_match["skill_id"], params={})
            _skill_output = _skill_result.get("output") or _skill_result.get("error") or ""
            _reply = (
                f"[Skill: **{_skill_match['name']}**]\n\n"
                + (str(_skill_output) if isinstance(_skill_output, str) else json.dumps(_skill_output, indent=2))
            )
            if stream:
                return StreamingResponse(
                    _stream_cached(
                        _reply, "skill-dispatch", "intent_router",
                        correlation_id, session_id, req_id
                    ),
                    media_type="text/event-stream",
                    headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
                )
            from app.core.envelopes import success as _ok
            return _ok(
                {
                    "messageId": f"msg_{uuid4()}",
                    "role": "assistant",
                    "content": _reply,
                    "model": "skill-dispatch",
                    "providerId": "intent_router",
                    "finishReason": "stop",
                    "usage": None,
                    "skillId": _skill_match["skill_id"],
                },
                correlation_id,
            )
    except Exception as _ir_exc:
        logger.debug("intent_router_skipped", reason=str(_ir_exc))

    # Inject JARVIS system prompt
    messages = inject_system_prompt(messages)

    if not model_id:
        return _json_error(400, "model_required", "No model specified and no default model available", correlation_id)

    logger.debug(
        "chat_pipeline_ready",
        mode=mode,
        model=model_id,
        latency_ms=round((time.monotonic() - t0) * 1000),
    )

    if stream:
        return StreamingResponse(
            _stream_events(
                providers, messages, model_id, max_tokens,
                correlation_id, session_id, req_id, db, user_id, cache,
            ),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    override_was_used = bool(getattr(settings, f"model_mode_{mode}_model_override", None))

    last_exc: Exception | None = None
    for provider in providers:
        current_model_id = model_id
        try:
            if last_exc is not None and override_was_used:
                try:
                    provider_models = await provider.list_models()
                    resolution = resolve_mode(mode, provider_models, overrides={})
                    if resolution:
                        current_model_id = resolution.modelId
                        override_was_used = False
                        logger.info(
                            "model_re_resolved_for_fallback",
                            provider=provider.provider_id,
                            mode=mode,
                            model=current_model_id,
                        )
                except Exception:
                    pass

            result = await provider.chat(messages, current_model_id, max_tokens)
            content = _extract_content(result)

            asyncio.ensure_future(_post_turn_update(db, user_msg_raw, content, session_id, user_id))
            if cache:
                await cache.set(messages, current_model_id, content)

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
            logger.warning("chat_provider_failed", provider=provider.provider_id, error=str(exc))
            last_exc = exc
            continue

    logger.error("chat_all_providers_failed", error=str(last_exc))
    return _json_error(502, "completion_error", f"All providers failed: {last_exc}", correlation_id)


# ── Stream helpers ────────────────────────────────────────────────────────────

async def _stream_cached(
    content: str,
    model_id: str,
    provider_id: str,
    correlation_id: str,
    session_id: str | None,
    req_id: str | None,
) -> Any:
    """Re-stream a cached response as SSE tokens so clients see no difference."""
    message_id = f"msg_{uuid4()}"
    yield _sse(new_event(
        "CHAT_STREAM_START",
        {"messageId": message_id, "model": model_id, "providerId": provider_id, "cached": True},
        correlation_id, req_id, session_id,
    ))
    # Chunk into ~10-char pieces to simulate streaming feel
    chunk_size = 10
    for i in range(0, len(content), chunk_size):
        token = content[i:i + chunk_size]
        yield _sse(new_event(
            "CHAT_STREAM_TOKEN",
            {"messageId": message_id, "token": token},
            correlation_id, req_id, session_id,
        ))
    yield _sse(new_event(
        "CHAT_STREAM_END",
        {"messageId": message_id, "content": content, "model": model_id, "providerId": provider_id, "cached": True},
        correlation_id, req_id, session_id,
    ))
    yield "data: [DONE]\n\n"


async def _stream_events(
    providers: list[Any],
    messages: list[dict],
    model_id: str,
    max_tokens: int | None,
    correlation_id: str,
    session_id: str | None,
    req_id: str | None,
    db: Any = None,
    user_id: str = "default",
    cache: Any = None,
) -> Any:
    message_id = f"msg_{uuid4()}"

    # Probe first token per provider to detect auth/conn errors before STREAM_START
    used_provider: Any = None
    stream_iter: Any = None
    first_token: str | None = None
    last_err: str = ""

    for provider in providers:
        try:
            candidate_iter = provider.stream_chat(messages, model_id, max_tokens)
            try:
                first_token = await asyncio.wait_for(
                    candidate_iter.__anext__(),
                    timeout=10.0,
                )
            except StopAsyncIteration:
                first_token = None
            stream_iter = candidate_iter
            used_provider = provider
            break
        except asyncio.TimeoutError:
            logger.warning("chat_stream_first_token_timeout", provider=provider.provider_id)
            last_err = "first-token timeout"
            continue
        except Exception as exc:
            logger.warning("chat_stream_provider_failed_init", provider=provider.provider_id, error=str(exc))
            last_err = str(exc)
            continue

    if used_provider is None or stream_iter is None:
        yield _sse(new_event(
            "CHAT_STREAM_ERROR",
            {"messageId": message_id, "error": f"All providers failed: {last_err}"},
            correlation_id, req_id, session_id,
        ))
        yield "data: [DONE]\n\n"
        return

    yield _sse(new_event(
        "CHAT_STREAM_START",
        {"messageId": message_id, "model": model_id, "providerId": used_provider.provider_id},
        correlation_id, req_id, session_id,
    ))

    full_content: list[str] = []

    def _emit_chunk(raw_chunk: str) -> str | None:
        try:
            chunk_data = json.loads(raw_chunk)
        except Exception:
            return None
        choices = chunk_data.get("choices", [{}])
        if not choices:
            return None
        token = choices[0].get("delta", {}).get("content", "")
        if not token:
            return None
        full_content.append(token)
        return _sse(new_event(
            "CHAT_STREAM_TOKEN",
            {"messageId": message_id, "token": token},
            correlation_id, req_id, session_id,
        ))

    try:
        if first_token is not None:
            evt = _emit_chunk(first_token)
            if evt:
                yield evt

        async for raw_chunk in stream_iter:
            evt = _emit_chunk(raw_chunk)
            if evt:
                yield evt
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
            "providerId": used_provider.provider_id,
        },
        correlation_id, req_id, session_id,
    ))
    yield "data: [DONE]\n\n"

    if assembled:
        user_msg = next(
            (m.get("content", "") for m in reversed(messages) if m.get("role") == "user"),
            "",
        )
        if db is not None:
            asyncio.ensure_future(_post_turn_update(db, user_msg, assembled, session_id, user_id))
        if cache:
            await cache.set(messages, model_id, assembled)


# ── Utilities ─────────────────────────────────────────────────────────────────

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


def _is_embedding_model(model_id: str) -> bool:
    lower = model_id.lower()
    return any(kw in lower for kw in _EMBEDDING_KEYWORDS)
