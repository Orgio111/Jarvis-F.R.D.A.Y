from __future__ import annotations

from typing import Any, AsyncIterator

import httpx

from app.core.config import Settings
from app.core.logging import get_logger
from app.providers.base import BaseProvider

logger = get_logger(__name__)


class NvidiaNIMProvider(BaseProvider):
    """
    NVIDIA NIM provider.
    Marked provider_unavailable when NVIDIA_NIM_API_KEY is empty or blank.
    All methods return safe defaults when unavailable — startup never fails.
    """

    def __init__(self, settings: Settings):
        self._api_key = settings.nvidia_nim_api_key.strip()
        self._base_url = settings.nvidia_nim_base_url.rstrip("/")
        self._timeout = settings.ai_provider_timeout_seconds
        self._available = bool(self._api_key and self._api_key != "replace_me")

        if not self._available:
            logger.info("provider_unavailable", provider="nvidia_nim", reason="API key not configured")

    @property
    def provider_id(self) -> str:
        return "nvidia_nim"

    @property
    def provider_name(self) -> str:
        return "NVIDIA NIM"

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
            logger.warning("nvidia_nim_list_models_failed", error=str(exc))
            return []

    def _map_model(self, raw: dict) -> dict:
        model_id = raw.get("id", "")
        return {
            "id": model_id,
            "name": raw.get("name", model_id),
            "providerId": "nvidia_nim",
            "providerName": "NVIDIA NIM",
            "groups": self._infer_groups(model_id),
            "contextWindow": raw.get("context_length", 8192),
            "maxTokens": raw.get("max_tokens", 4096),
            "supportsVision": "vision" in model_id.lower() or "vl" in model_id.lower(),
            "supportsTools": True,
            "deviceMode": "cloud",
            "isDefault": False,
            "isFree": False,
        }

    def _infer_groups(self, model_id: str) -> list[str]:
        groups = []
        m = model_id.lower()
        if any(x in m for x in ["llama", "mixtral", "mistral"]):
            groups.append("fastest_chat")
        if any(x in m for x in ["70b", "405b", "claude"]):
            groups.append("deep_reasoning")
        if any(x in m for x in ["code", "coder", "starcoder", "deepseek"]):
            groups.append("coding")
        if "vision" in m or "vl" in m:
            groups.append("vision")
        if "embed" in m:
            groups.append("embedding")
        return groups or ["fastest_chat"]

    async def chat(self, messages: list[dict], model_id: str, max_tokens: int | None = None, **kwargs: Any) -> dict:
        if not self._available:
            raise RuntimeError("nvidia_nim provider is unavailable")
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
        self, messages: list[dict], model_id: str, max_tokens: int | None = None, **kwargs: Any
    ) -> AsyncIterator[str]:
        if not self._available:
            raise RuntimeError("nvidia_nim provider is unavailable")
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
