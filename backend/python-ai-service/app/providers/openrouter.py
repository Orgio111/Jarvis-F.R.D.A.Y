from __future__ import annotations

from typing import Any, AsyncIterator

import httpx

from app.core.config import Settings
from app.core.logging import get_logger
from app.providers.base import BaseProvider

logger = get_logger(__name__)


class OpenRouterProvider(BaseProvider):
    """
    OpenRouter provider.
    Marked provider_unavailable when OPENROUTER_API_KEY is empty or blank.
    """

    def __init__(self, settings: Settings):
        self._api_key = settings.openrouter_api_key.strip()
        self._base_url = settings.openrouter_base_url.rstrip("/")
        self._timeout = settings.ai_provider_timeout_seconds
        self._available = bool(self._api_key and self._api_key != "replace_me")

        if not self._available:
            logger.info("provider_unavailable", provider="openrouter", reason="API key not configured")

    @property
    def provider_id(self) -> str:
        return "openrouter"

    @property
    def provider_name(self) -> str:
        return "OpenRouter"

    @property
    def device_mode(self) -> str:
        return "cloud" if self._available else "disabled"

    async def health_check(self) -> dict:
        if not self._available:
            return {"status": "provider_unavailable", "reason": "API key not configured"}
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                r = await client.get(
                    f"{self._base_url}/models",
                    headers={"Authorization": f"Bearer {self._api_key}"},
                )
            if r.status_code == 200:
                return {"status": "available", "reason": None}
            return {"status": "error", "reason": f"HTTP {r.status_code}"}
        except Exception as exc:
            return {"status": "error", "reason": str(exc)}

    async def list_models(self) -> list[dict]:
        if not self._available:
            return []
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                r = await client.get(
                    f"{self._base_url}/models",
                    headers={"Authorization": f"Bearer {self._api_key}"},
                )
            if r.status_code != 200:
                return []
            data = r.json()
            raw_models = data.get("data", [])
            return [self._map_model(m) for m in raw_models]
        except Exception as exc:
            logger.warning("openrouter_list_models_failed", error=str(exc))
            return []

    def _map_model(self, raw: dict) -> dict:
        model_id = raw.get("id", "")
        pricing = raw.get("pricing", {})
        prompt_cost = float(pricing.get("prompt", "0") or 0)
        return {
            "id": model_id,
            "name": raw.get("name", model_id),
            "providerId": "openrouter",
            "providerName": "OpenRouter",
            "groups": self._infer_groups(model_id, raw),
            "contextWindow": raw.get("context_length", 8192),
            "maxTokens": raw.get("top_provider", {}).get("max_completion_tokens", 4096),
            "supportsVision": "vision" in (raw.get("description", "") or "").lower()
                              or "vision" in model_id.lower(),
            "supportsTools": True,
            "deviceMode": "cloud",
            "isDefault": False,
            "isFree": prompt_cost == 0.0,
            "description": raw.get("description", ""),
        }

    def _infer_groups(self, model_id: str, raw: dict) -> list[str]:
        groups = []
        m = model_id.lower()
        desc = (raw.get("description") or "").lower()
        if raw.get("pricing", {}).get("prompt", "1") == "0":
            groups.append("cheap_or_free")
            groups.append("fallback_safe")
        if any(x in m for x in ["llama", "phi", "gemma", "mistral"]):
            groups.append("fastest_chat")
        if any(x in m for x in ["70b", "opus", "gpt-4", "sonnet"]):
            groups.append("deep_reasoning")
        if any(x in m for x in ["code", "coder", "deepseek"]):
            groups.append("coding")
        if "vision" in desc or "vision" in m:
            groups.append("vision")
        return groups or ["fastest_chat", "fallback_safe"]

    async def chat(self, messages: list[dict], model_id: str, max_tokens: int | None = None, **kwargs: Any) -> dict:
        if not self._available:
            raise RuntimeError("openrouter provider is unavailable")
        payload: dict[str, Any] = {"model": model_id, "messages": messages}
        if max_tokens:
            payload["max_tokens"] = max_tokens
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            r = await client.post(
                f"{self._base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "HTTP-Referer": "https://jarvis.local",
                    "X-Title": "JARVIS",
                    "Content-Type": "application/json",
                },
                json=payload,
            )
        r.raise_for_status()
        return r.json()

    async def stream_chat(
        self, messages: list[dict], model_id: str, max_tokens: int | None = None, **kwargs: Any
    ) -> AsyncIterator[str]:
        if not self._available:
            raise RuntimeError("openrouter provider is unavailable")
        payload: dict[str, Any] = {"model": model_id, "messages": messages, "stream": True}
        if max_tokens:
            payload["max_tokens"] = max_tokens
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            async with client.stream(
                "POST",
                f"{self._base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "HTTP-Referer": "https://jarvis.local",
                    "X-Title": "JARVIS",
                    "Content-Type": "application/json",
                },
                json=payload,
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if line.startswith("data: ") and not line.endswith("[DONE]"):
                        yield line[6:]
