from __future__ import annotations

import json
import re
from typing import Any, AsyncIterator

from app.core.config import Settings
from app.core.logging import get_logger
from app.providers.base import BaseProvider

logger = get_logger(__name__)

try:
    import anthropic as _anthropic
    _SDK_AVAILABLE = True
except ImportError:
    _anthropic = None  # type: ignore[assignment]
    _SDK_AVAILABLE = False

_DEFAULT_MODEL = "claude-opus-4-7"
_THINKING_MODELS = frozenset({"claude-opus-4-7", "claude-opus-4-6", "claude-sonnet-4-6"})

_STATIC_MODELS: list[dict] = [
    {
        "id": "claude-opus-4-7",
        "name": "Claude Opus 4.7",
        "providerId": "anthropic",
        "providerName": "Anthropic",
        "groups": ["deep_reasoning", "coding", "vision"],
        "contextWindow": 1_048_576,
        "maxTokens": 64000,
        "supportsVision": True,
        "supportsTools": True,
        "deviceMode": "cloud",
        "isDefault": True,
        "isFree": False,
    },
    {
        "id": "claude-opus-4-6",
        "name": "Claude Opus 4.6",
        "providerId": "anthropic",
        "providerName": "Anthropic",
        "groups": ["deep_reasoning", "coding", "vision"],
        "contextWindow": 1_048_576,
        "maxTokens": 32000,
        "supportsVision": True,
        "supportsTools": True,
        "deviceMode": "cloud",
        "isDefault": False,
        "isFree": False,
    },
    {
        "id": "claude-sonnet-4-6",
        "name": "Claude Sonnet 4.6",
        "providerId": "anthropic",
        "providerName": "Anthropic",
        "groups": ["fastest_chat", "coding", "vision"],
        "contextWindow": 1_048_576,
        "maxTokens": 16000,
        "supportsVision": True,
        "supportsTools": True,
        "deviceMode": "cloud",
        "isDefault": False,
        "isFree": False,
    },
    {
        "id": "claude-haiku-4-5",
        "name": "Claude Haiku 4.5",
        "providerId": "anthropic",
        "providerName": "Anthropic",
        "groups": ["fastest_chat"],
        "contextWindow": 204_800,
        "maxTokens": 8192,
        "supportsVision": True,
        "supportsTools": True,
        "deviceMode": "cloud",
        "isDefault": False,
        "isFree": False,
    },
]


class AnthropicProvider(BaseProvider):
    """
    Anthropic provider using the official Anthropic SDK.
    Marked provider_unavailable when ANTHROPIC_API_KEY is empty or the SDK is missing.
    Supports prompt caching on system messages, vision (image_url → image blocks),
    and adaptive thinking on Opus/Sonnet 4.x models.
    """

    def __init__(self, settings: Settings):
        self._api_key = settings.anthropic_api_key.strip()
        self._timeout = settings.ai_provider_timeout_seconds
        self._available = bool(self._api_key and self._api_key != "replace_me" and _SDK_AVAILABLE)

        if not self._available:
            reason = "anthropic SDK not installed" if not _SDK_AVAILABLE else "API key not configured"
            logger.info("provider_unavailable", provider="anthropic", reason=reason)

    # ── BaseProvider properties ───────────────────────────────────────────────

    @property
    def provider_id(self) -> str:
        return "anthropic"

    @property
    def provider_name(self) -> str:
        return "Anthropic"

    @property
    def device_mode(self) -> str:
        return "cloud" if self._available else "disabled"

    # ── BaseProvider methods ──────────────────────────────────────────────────

    async def health_check(self) -> dict:
        if not self._available:
            return {"status": "provider_unavailable", "reason": "API key not configured"}
        try:
            client = _anthropic.AsyncAnthropic(api_key=self._api_key)
            await client.models.list()
            return {"status": "available", "reason": None}
        except Exception as exc:
            return {"status": "error", "reason": str(exc)}

    async def list_models(self) -> list[dict]:
        if not self._available:
            return []
        try:
            client = _anthropic.AsyncAnthropic(api_key=self._api_key)
            page = await client.models.list()
            live = []
            for m in page.data:
                live.append({
                    "id": m.id,
                    "name": getattr(m, "display_name", m.id),
                    "providerId": "anthropic",
                    "providerName": "Anthropic",
                    "groups": self._infer_groups(m.id),
                    "contextWindow": 1_048_576,
                    "maxTokens": 64000,
                    "supportsVision": True,
                    "supportsTools": True,
                    "deviceMode": "cloud",
                    "isDefault": m.id == _DEFAULT_MODEL,
                    "isFree": False,
                })
            return live if live else _STATIC_MODELS
        except Exception as exc:
            logger.warning("anthropic_list_models_failed", error=str(exc))
            return _STATIC_MODELS

    async def chat(
        self,
        messages: list[dict],
        model_id: str,
        max_tokens: int | None = None,
        **kwargs: Any,
    ) -> dict:
        if not self._available:
            raise RuntimeError("anthropic provider is unavailable")

        model_id = model_id or _DEFAULT_MODEL
        max_tokens = max_tokens or 8192
        system, converted = self._split_messages(messages)

        create_kwargs: dict[str, Any] = {
            "model": model_id,
            "max_tokens": max_tokens,
            "messages": converted,
        }
        if system:
            create_kwargs["system"] = system
        if model_id in _THINKING_MODELS:
            create_kwargs["thinking"] = {"type": "adaptive"}

        client = _anthropic.AsyncAnthropic(api_key=self._api_key)
        response = await client.messages.create(**create_kwargs)

        content = "".join(
            block.text for block in response.content if hasattr(block, "text")
        )
        return {
            "choices": [{
                "message": {"role": "assistant", "content": content},
                "finish_reason": response.stop_reason or "stop",
            }],
            "usage": {
                "prompt_tokens": response.usage.input_tokens,
                "completion_tokens": response.usage.output_tokens,
                "total_tokens": response.usage.input_tokens + response.usage.output_tokens,
            },
        }

    async def stream_chat(
        self,
        messages: list[dict],
        model_id: str,
        max_tokens: int | None = None,
        **kwargs: Any,
    ) -> AsyncIterator[str]:
        if not self._available:
            raise RuntimeError("anthropic provider is unavailable")

        model_id = model_id or _DEFAULT_MODEL
        max_tokens = max_tokens or 8192
        system, converted = self._split_messages(messages)

        create_kwargs: dict[str, Any] = {
            "model": model_id,
            "max_tokens": max_tokens,
            "messages": converted,
        }
        if system:
            create_kwargs["system"] = system
        if model_id in _THINKING_MODELS:
            create_kwargs["thinking"] = {"type": "adaptive"}

        client = _anthropic.AsyncAnthropic(api_key=self._api_key)
        async with client.messages.stream(**create_kwargs) as stream:
            async for text in stream.text_stream:
                yield json.dumps({"choices": [{"delta": {"content": text}}]})

    # ── message conversion helpers ────────────────────────────────────────────

    def _split_messages(
        self, messages: list[dict]
    ) -> tuple[list[dict] | None, list[dict]]:
        """Extract system messages and apply prompt caching; return (system, user_messages)."""
        system_parts: list[str] = []
        user_messages: list[dict] = []

        for m in messages:
            if m.get("role") == "system":
                content = m.get("content", "")
                if isinstance(content, str) and content:
                    system_parts.append(content)
            else:
                user_messages.append(self._convert_message(m))

        if not system_parts:
            return None, user_messages

        combined = "\n\n".join(system_parts)
        system = [{"type": "text", "text": combined, "cache_control": {"type": "ephemeral"}}]
        return system, user_messages

    def _convert_message(self, msg: dict) -> dict:
        """Convert an OpenAI-format message content to Anthropic format."""
        role = msg.get("role", "user")
        content = msg.get("content", "")

        if isinstance(content, str):
            return {"role": role, "content": content}

        parts: list[dict] = []
        for part in content:
            part_type = part.get("type", "")
            if part_type == "text":
                parts.append({"type": "text", "text": part.get("text", "")})
            elif part_type == "image_url":
                block = self._convert_image_url(part.get("image_url", {}))
                if block:
                    parts.append(block)

        return {"role": role, "content": parts}

    def _convert_image_url(self, image_url: dict) -> dict | None:
        """Convert an OpenAI image_url part to an Anthropic image block."""
        url = image_url.get("url", "")

        match = re.match(r"data:([^;]+);base64,(.+)", url, re.DOTALL)
        if match:
            return {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": match.group(1),
                    "data": match.group(2).strip(),
                },
            }

        if url.startswith("http"):
            return {"type": "image", "source": {"type": "url", "url": url}}

        return None

    def _infer_groups(self, model_id: str) -> list[str]:
        m = model_id.lower()
        if "opus" in m:
            return ["deep_reasoning", "coding", "vision"]
        if "sonnet" in m:
            return ["fastest_chat", "coding", "vision"]
        if "haiku" in m:
            return ["fastest_chat"]
        return ["fastest_chat"]
