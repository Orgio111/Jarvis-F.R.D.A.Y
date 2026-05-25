"""
DiscoveredProvider — wraps a dynamically discovered ProviderEndpoint
as a full BaseProvider, making it available for chat routing.

Most discovered endpoints use the OpenAI-compatible API format.
Anthropic-format endpoints are intentionally excluded since Anthropic
is already covered by the static AnthropicProvider.
"""

from __future__ import annotations

import json
from typing import Any, AsyncIterator

import httpx

from app.core.config import Settings
from app.core.logging import get_logger
from app.providers.base import BaseProvider
from app.provider_discovery.discovery import ProviderEndpoint, get_discoverer

logger = get_logger(__name__)


class DiscoveredProvider(BaseProvider):
    """
    Wraps a ProviderEndpoint as a full BaseProvider for chat routing.

    Only supports OpenAI-compatible API format (api_type == "openai").
    Anthropic-format discovered endpoints are skipped — they are covered
    by the static AnthropicProvider.
    """

    def __init__(self, endpoint: ProviderEndpoint, settings: Settings):
        self._endpoint = endpoint
        self._settings = settings
        self._timeout = settings.ai_provider_timeout_seconds
        self._http = httpx.AsyncClient(timeout=self._timeout)

    # ── BaseProvider properties ───────────────────────────────────────────────

    @property
    def provider_id(self) -> str:
        slug = self._endpoint.name.lower().replace(" ", "_").replace("-", "_")
        return f"discovered:{slug}"

    @property
    def provider_name(self) -> str:
        return self._endpoint.name

    @property
    def device_mode(self) -> str:
        return "cloud"

    def is_available(self) -> bool:
        return self._endpoint.is_available

    # ── BaseProvider methods ──────────────────────────────────────────────────

    async def health_check(self) -> dict:
        if not self._endpoint.is_available:
            return {"status": "provider_unavailable", "reason": "Not available on last discovery sweep"}
        return {"status": "available", "reason": None}

    async def list_models(self) -> list[dict]:
        if not self._endpoint.is_available:
            return []
        return [
            {
                "id": m,
                "name": m,
                "providerId": self.provider_id,
                "providerName": self.provider_name,
                "groups": self._infer_groups(m),
                "contextWindow": 8192,
                "maxTokens": 4096,
                "supportsVision": "vision" in m.lower() or "vl" in m.lower(),
                "supportsTools": True,
                "deviceMode": "cloud",
                "isDefault": False,
                "isFree": self._endpoint.is_free,
            }
            for m in self._endpoint.models
        ]

    async def chat(
        self,
        messages: list[dict],
        model_id: str,
        max_tokens: int | None = None,
        **kwargs: Any,
    ) -> dict:
        if not self._endpoint.is_available:
            raise RuntimeError(f"discovered provider '{self.provider_name}' is unavailable")

        headers = self._auth_headers()
        headers["Content-Type"] = "application/json"

        payload: dict[str, Any] = {"model": model_id, "messages": messages}
        if max_tokens:
            payload["max_tokens"] = max_tokens

        url = f"{self._endpoint.base_url}/chat/completions"
        logger.debug("discovered_provider_chat", provider=self.provider_name, url=url, model=model_id)

        try:
            resp = await self._http.post(url, json=payload, headers=headers)
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPStatusError as exc:
            body = await exc.response.aread()
            raise RuntimeError(
                f"discovered provider '{self.provider_name}' HTTP {exc.response.status_code}: "
                f"{body.decode(errors='replace')[:200]}"
            )
        except httpx.RequestError as exc:
            raise RuntimeError(
                f"discovered provider '{self.provider_name}' unreachable: {exc}"
            )

    async def stream_chat(
        self,
        messages: list[dict],
        model_id: str,
        max_tokens: int | None = None,
        **kwargs: Any,
    ) -> AsyncIterator[str]:
        if not self._endpoint.is_available:
            raise RuntimeError(f"discovered provider '{self.provider_name}' is unavailable")

        headers = self._auth_headers()
        headers["Content-Type"] = "application/json"

        payload: dict[str, Any] = {"model": model_id, "messages": messages, "stream": True}
        if max_tokens:
            payload["max_tokens"] = max_tokens

        url = f"{self._endpoint.base_url}/chat/completions"
        logger.debug("discovered_provider_stream", provider=self.provider_name, url=url, model=model_id)

        try:
            async with self._http.stream("POST", url, json=payload, headers=headers) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if line.startswith("data: ") and not line.endswith("[DONE]"):
                        yield line[6:]
        except httpx.HTTPStatusError as exc:
            body = await exc.response.aread()
            raise RuntimeError(
                f"discovered provider '{self.provider_name}' HTTP {exc.response.status_code}: "
                f"{body.decode(errors='replace')[:200]}"
            )
        except httpx.RequestError as exc:
            raise RuntimeError(
                f"discovered provider '{self.provider_name}' unreachable: {exc}"
            )

    # ── helpers ───────────────────────────────────────────────────────────────

    def get_endpoint_summary(self) -> dict:
        """Return a public summary of the underlying endpoint metadata."""
        return {
            "name": self._endpoint.name,
            "baseUrl": self._endpoint.base_url,
            "apiType": self._endpoint.api_type,
            "capabilities": sorted(list(self._endpoint.capabilities)),
            "isFree": self._endpoint.is_free,
            "isAvailable": self._endpoint.is_available,
            "latencyMs": round(self._endpoint.latency_ms, 1),
            "score": round(self._endpoint.score, 1),
            "modelCount": len(self._endpoint.models),
            "models": self._endpoint.models[:30] if self._endpoint.models else [],
            "lastChecked": self._endpoint.last_checked,
        }

    def _auth_headers(self) -> dict[str, str]:
        """Get auth headers for this discovered provider."""
        from app.provider_discovery.discovery import get_discoverer
        discoverer = get_discoverer()
        return discoverer.get_auth_for_provider(self._endpoint.name)

    def _infer_groups(self, model_id: str) -> list[str]:
        m = model_id.lower()
        groups: list[str] = []
        if any(x in m for x in ("llama", "phi", "gemma", "mistral", "mixtral")):
            groups.append("fastest_chat")
        if any(x in m for x in ("70b", "405b", "opus", "sonnet", "gpt-4", "deepseek")):
            groups.append("deep_reasoning")
        if any(x in m for x in ("code", "coder", "starcoder", "deepseek")):
            groups.append("coding")
        if any(x in m for x in ("vision", "vl", "multi-modal")):
            groups.append("vision")
        if self._endpoint.is_free:
            groups.append("cheap_or_free")
            groups.append("fallback_safe")
        return groups or ["fastest_chat", "fallback_safe"]

    async def close(self) -> None:
        await self._http.aclose()
