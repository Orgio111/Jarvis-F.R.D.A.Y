"""
Provider Discovery — automatically discovers and catalogs available LLM providers.

Mirrors patterns from free-llm-api-resources to build a dynamic provider registry
with latency scoring, capability detection, and automatic registration.
"""

from __future__ import annotations

import asyncio
import json
import time
import uuid
from dataclasses import dataclass, field
from typing import Any

import httpx

from app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class ProviderEndpoint:
    """A discovered provider endpoint with capabilities and health."""

    name: str
    base_url: str
    api_type: str  # openai, anthropic, nvidia, ollama, custom
    models: list[str] = field(default_factory=list)
    capabilities: set[str] = field(default_factory=set)
    latency_ms: float = 0.0
    is_free: bool = True
    is_available: bool = False
    last_checked: float = 0.0
    error_rate: float = 0.0
    score: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)


class ProviderDiscoverer:
    """
    Discovers, catalogs, and scores LLM providers automatically.

    Uses known public endpoints and dynamic discovery patterns to build
    a comprehensive provider registry with health and capability scoring.
    """

    # Known free/open provider endpoints
    KNOWN_PROVIDERS: list[dict[str, Any]] = [
        {"name": "OpenRouter Free", "base_url": "https://openrouter.ai/api/v1", "api_type": "openai", "is_free": True},
        {"name": "NVIDIA NIM", "base_url": "https://integrate.api.nvidia.com/v1", "api_type": "openai", "is_free": False},
        {"name": "Ollama Local", "base_url": "http://localhost:11434/v1", "api_type": "openai", "is_free": True},
        {"name": "Groq Free", "base_url": "https://api.groq.com/openai/v1", "api_type": "openai", "is_free": True},
        {"name": "DeepSeek", "base_url": "https://api.deepseek.com/v1", "api_type": "openai", "is_free": False},
        {"name": "Together AI", "base_url": "https://api.together.xyz/v1", "api_type": "openai", "is_free": False},
        {"name": "Anthropic Direct", "base_url": "https://api.anthropic.com/v1", "api_type": "anthropic", "is_free": False},
        {"name": "OpenAI Direct", "base_url": "https://api.openai.com/v1", "api_type": "openai", "is_free": False},
        {"name": "Mistral AI", "base_url": "https://api.mistral.ai/v1", "api_type": "openai", "is_free": False},
        {"name": "Fireworks AI", "base_url": "https://api.fireworks.ai/inference/v1", "api_type": "openai", "is_free": False},
    ]

    def __init__(self):
        self._endpoints: dict[str, ProviderEndpoint] = {}
        self._http = httpx.AsyncClient(timeout=5.0)
        self._discovery_lock = asyncio.Lock()

    async def discover_all(self) -> list[ProviderEndpoint]:
        """Discover and health-check all known providers."""
        async with self._discovery_lock:
            tasks = [self._check_provider(p) for p in self.KNOWN_PROVIDERS]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            endpoints: list[ProviderEndpoint] = []
            for result in results:
                if isinstance(result, ProviderEndpoint):
                    endpoints.append(result)
                elif isinstance(result, Exception):
                    logger.debug("provider_discovery_error", error=str(result))

            # Sort by score descending
            endpoints.sort(key=lambda e: e.score, reverse=True)
            for ep in endpoints:
                self._endpoints[ep.name] = ep

            logger.info("provider_discovery_complete", count=len(endpoints), available=sum(1 for e in endpoints if e.is_available))
            return endpoints

    async def _check_provider(self, provider_info: dict[str, Any]) -> ProviderEndpoint:
        """Check a single provider's availability and capabilities."""
        ep = ProviderEndpoint(
            name=provider_info["name"],
            base_url=provider_info["base_url"],
            api_type=provider_info["api_type"],
            is_free=provider_info.get("is_free", True),
        )

        start = time.perf_counter()
        try:
            # Try to fetch models endpoint — use configured API key if available
            headers = self.get_auth_for_provider(ep.name)
            response = await self._http.get(
                f"{ep.base_url}/models",
                headers=headers,
                timeout=5.0,
            )

            latency = (time.perf_counter() - start) * 1000
            ep.latency_ms = latency
            ep.last_checked = time.time()

            if response.status_code == 200:
                ep.is_available = True
                data = response.json()
                models = data.get("data", data.get("models", []))
                ep.models = [m.get("id", "") for m in models if isinstance(m, dict)][:20]

                # Detect capabilities from model names
                for model_id in ep.models:
                    model_lower = model_id.lower()
                    if any(k in model_lower for k in ["vision", "multi-modal", "gemini"]):
                        ep.capabilities.add("vision")
                    if any(k in model_lower for k in ["code", "coder", "deepseek"]):
                        ep.capabilities.add("coding")
                    if any(k in model_lower for k in ["embed", "ada"]):
                        ep.capabilities.add("embeddings")
                    if any(k in model_lower for k in ["image", "dall-e", "stable"]):
                        ep.capabilities.add("image")
                    if any(k in model_lower for k in ["tts", "whisper", "speech"]):
                        ep.capabilities.add("audio")

                # Score: higher is better
                ep.score = self._compute_score(ep)
            else:
                ep.is_available = False
                ep.score = 0.0

        except Exception as exc:
            ep.is_available = False
            ep.score = 0.0
            ep.latency_ms = -1
            logger.debug("provider_unreachable", name=ep.name, error=str(exc))

        return ep

    def get_auth_for_provider(self, provider_name: str) -> dict[str, str]:
        """
        Get auth headers for a provider based on configured API keys.

        Public method — used by DiscoveredProvider and any other consumer
        that needs to authenticate against discovered endpoints.
        """
        from app.core.config import get_settings
        s = get_settings()
        key_map = {
            "OpenAI Direct": s.openai_api_key,
            "Anthropic Direct": s.anthropic_api_key,
            "NVIDIA NIM": s.nvidia_nim_api_key,
            "OpenRouter Free": s.openrouter_api_key,
            "DeepSeek": s.openai_api_key,
        }
        key = key_map.get(provider_name, "")
        if key:
            return {"Authorization": f"Bearer {key}"}
        return {}

    def _compute_score(self, ep: ProviderEndpoint) -> float:
        """Compute a composite score for a provider."""
        score = 0.0

        # Latency score (lower is better)
        if ep.latency_ms > 0:
            if ep.latency_ms < 200:
                score += 30
            elif ep.latency_ms < 500:
                score += 20
            elif ep.latency_ms < 1000:
                score += 10
            else:
                score += 5

        # Free tier bonus
        if ep.is_free:
            score += 25

        # Model count
        score += min(len(ep.models), 10) * 2

        # Capability diversity
        score += len(ep.capabilities) * 5

        # Availability
        if ep.is_available:
            score += 20

        return score

    async def get_best_providers(self, capability: str | None = None, limit: int = 3) -> list[ProviderEndpoint]:
        """Get the best available providers, optionally filtered by capability."""
        candidates = [e for e in self._endpoints.values() if e.is_available]
        if capability:
            candidates = [e for e in candidates if capability in e.capabilities]
        candidates.sort(key=lambda e: e.score, reverse=True)
        return candidates[:limit]

    async def get_all(self) -> list[ProviderEndpoint]:
        return list(self._endpoints.values())

    async def close(self) -> None:
        await self._http.aclose()


# Singleton
_discoverer_instance: ProviderDiscoverer | None = None


def get_discoverer() -> ProviderDiscoverer:
    global _discoverer_instance
    if _discoverer_instance is None:
        _discoverer_instance = ProviderDiscoverer()
    return _discoverer_instance
