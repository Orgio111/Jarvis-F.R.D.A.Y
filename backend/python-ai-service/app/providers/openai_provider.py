from __future__ import annotations

from typing import Any, AsyncIterator

import httpx

from app.core.config import Settings
from app.core.logging import get_logger
from app.providers.base import BaseProvider

logger = get_logger(__name__)


class OpenAIProvider(BaseProvider):
    """
    OpenAI provider using httpx against the OpenAI API.
    Marked provider_unavailable when OPENAI_API_KEY is empty or blank.
    All methods return safe defaults when unavailable — startup never fails.
    """

    def __init__(self, settings: Settings):
        self._api_key = settings.openai_api_key.strip()
        self._base_url = settings.openai_base_url.rstrip("/")
        self._timeout = settings.ai_provider_timeout_seconds
        self._available = bool(self._api_key and self._api_key != "replace_me")

        if not self._available:
            logger.info("provider_unavailable", provider="openai", reason="API key not configured")

    @property
    def provider_id(self) -> str:
        return "openai"

    @property
    def provider_name(self) -> str:
        return "OpenAI"

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
            raw_models = r.json().get("data", [])
            return [
                self._map_model(m)
                for m in raw_models
                if self._is_chat_model(m.get("id", ""))
            ]
        except Exception as exc:
            logger.warning("openai_list_models_failed", error=str(exc))
            return []

    def _is_chat_model(self, model_id: str) -> bool:
        m = model_id.lower()
        return any(prefix in m for prefix in ("gpt-4", "gpt-3.5", "o1", "o3", "o4"))

    def _map_model(self, raw: dict) -> dict:
        model_id = raw.get("id", "")
        m = model_id.lower()
        return {
            "id": model_id,
            "name": model_id,
            "providerId": "openai",
            "providerName": "OpenAI",
            "groups": self._infer_groups(m),
            "contextWindow": 128_000,
            "maxTokens": 16_384,
            "supportsVision": any(x in m for x in ("4o", "vision", "o1", "o3")),
            "supportsTools": True,
            "deviceMode": "cloud",
            "isDefault": model_id == "gpt-4o",
            "isFree": False,
        }

    def _infer_groups(self, model_id: str) -> list[str]:
        groups: list[str] = []
        if any(x in model_id for x in ("o1", "o3", "o4")):
            groups.append("deep_reasoning")
        if "gpt" in model_id:
            groups.append("fastest_chat")
        if any(x in model_id for x in ("gpt-4", "4o")):
            groups.append("coding")
        if any(x in model_id for x in ("4o", "vision", "o1", "o3")):
            groups.append("vision")
        return groups or ["fastest_chat"]

    async def chat(
        self,
        messages: list[dict],
        model_id: str,
        max_tokens: int | None = None,
        **kwargs: Any,
    ) -> dict:
        if not self._available:
            raise RuntimeError("openai provider is unavailable")
        payload: dict[str, Any] = {"model": model_id, "messages": messages}
        if max_tokens:
            payload["max_tokens"] = max_tokens
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            r = await client.post(
                f"{self._base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )
        r.raise_for_status()
        return r.json()

    async def stream_chat(
        self,
        messages: list[dict],
        model_id: str,
        max_tokens: int | None = None,
        **kwargs: Any,
    ) -> AsyncIterator[str]:
        if not self._available:
            raise RuntimeError("openai provider is unavailable")
        payload: dict[str, Any] = {"model": model_id, "messages": messages, "stream": True}
        if max_tokens:
            payload["max_tokens"] = max_tokens
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            async with client.stream(
                "POST",
                f"{self._base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if line.startswith("data: ") and not line.endswith("[DONE]"):
                        yield line[6:]
