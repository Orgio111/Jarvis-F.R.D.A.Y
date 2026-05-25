from __future__ import annotations

from typing import TYPE_CHECKING

from app.core.config import Settings
from app.core.logging import get_logger
from app.providers.anthropic_provider import AnthropicProvider
from app.providers.nvidia_nim import NvidiaNIMProvider
from app.providers.openai_provider import OpenAIProvider
from app.providers.openrouter import OpenRouterProvider

if TYPE_CHECKING:
    from app.providers.base import BaseProvider

logger = get_logger(__name__)


_DISCOVERED_PREFIX = "discovered:"


def _is_discovered_id(provider_id: str) -> bool:
    return provider_id.startswith(_DISCOVERED_PREFIX)


class ProviderRouter:
    """
    Selects the right provider for a given request.
    If the primary provider is unavailable, falls back to secondary.
    Supports dynamic discovered providers as additional fallback options.
    """

    _instance: "ProviderRouter | None" = None

    def __init__(self, settings: Settings):
        self._settings = settings
        self._providers: dict[str, "BaseProvider"] = {}  # static providers
        self._discovered: dict[str, "BaseProvider"] = {}  # dynamically discovered
        self._build_providers()

    def _build_providers(self) -> None:
        anthropic = AnthropicProvider(self._settings)
        nim = NvidiaNIMProvider(self._settings)
        openai = OpenAIProvider(self._settings)
        openrouter = OpenRouterProvider(self._settings)
        self._providers = {
            anthropic.provider_id: anthropic,
            nim.provider_id: nim,
            openai.provider_id: openai,
            openrouter.provider_id: openrouter,
        }

    @classmethod
    def initialize(cls, settings: Settings) -> "ProviderRouter":
        cls._instance = cls(settings)
        return cls._instance

    @classmethod
    def get(cls) -> "ProviderRouter":
        if cls._instance is None:
            raise RuntimeError("ProviderRouter not initialised")
        return cls._instance

    # ── Discovered provider integration ────────────────────────────────────────

    async def sync_discovered(self) -> int:
        """
        Run provider discovery and register discovered providers as fallback options.
        Skips providers already covered by static config (NVIDIA, OpenRouter, OpenAI, Anthropic).
        Returns the number of newly discovered providers registered.
        """
        from app.provider_discovery.discovery import get_discoverer
        from app.providers.discovered_provider import DiscoveredProvider

        discoverer = get_discoverer()
        endpoints = await discoverer.discover_all()

        # Skip providers already covered by static config
        # Match by: (1) exact name overlap, (2) substring name match (e.g. "OpenAI" in "OpenAI Direct"), (3) anthropic API type
        static_names_lower = {p.provider_name.lower() for p in self._providers.values()}

        count = 0
        for ep in endpoints:
            # Skip if api_type is anthropic (handled by static AnthropicProvider)
            if ep.api_type == "anthropic":
                continue

            # Skip if name matches any static provider name
            if ep.name.lower() in static_names_lower:
                continue

            # Skip if name contains a static provider name (e.g. "OpenAI Direct" contains "openai")
            ep_name_lower = ep.name.lower()
            if any(static_name in ep_name_lower for static_name in static_names_lower):
                continue

            provider = DiscoveredProvider(ep, self._settings)
            self._discovered[provider.provider_id] = provider
            count += 1

        logger.info(
            "discovered_providers_synced",
            count=count,
            total_discovered=len(self._discovered),
        )
        return count

    def get_discovered_providers(self) -> list["BaseProvider"]:
        return list(self._discovered.values())

    # ── Provider lookup ────────────────────────────────────────────────────────

    def get_provider(self, provider_id: str) -> "BaseProvider | None":
        if _is_discovered_id(provider_id):
            return self._discovered.get(provider_id)
        return self._providers.get(provider_id)

    def get_active_provider(self) -> "BaseProvider | None":
        providers = self.get_providers_in_priority_order()
        return providers[0] if providers else None

    def get_providers_in_priority_order(self) -> "list[BaseProvider]":
        """
        Returns available providers in priority order:
          1. Primary static provider
          2. Fallback static provider
          3. All available discovered providers (sorted by discovery score)
        """
        mode = self._settings.ai_provider_routing_mode
        primary_id = self._settings.ai_provider_primary
        fallback_id = self._settings.ai_provider_fallback

        result: list[BaseProvider] = []

        # ── Static providers (primary / fallback) ──
        if mode == "primary":
            p = self._providers.get(primary_id)
            if p and p.is_available():
                result.append(p)
        elif mode == "fallback":
            p = self._providers.get(fallback_id)
            if p and p.is_available():
                result.append(p)
        else:  # auto
            primary = self._providers.get(primary_id)
            if primary and primary.is_available():
                result.append(primary)
            fallback = self._providers.get(fallback_id)
            if fallback and fallback.is_available():
                result.append(fallback)

        # ── Discovered providers (additional fallbacks) ──
        if self._discovered:
            discovered_sorted = sorted(
                [d for d in self._discovered.values() if d.is_available()],
                key=lambda d: d.provider_id,  # stable sort order
            )
            result.extend(discovered_sorted)

        return result

    def get_all_providers(self) -> list["BaseProvider"]:
        return list(self._providers.values()) + list(self._discovered.values())

    async def get_all_statuses(self) -> list[dict]:
        statuses = []
        for p in self._providers.values():
            health = await p.health_check()
            statuses.append(
                {
                    "id": p.provider_id,
                    "name": p.provider_name,
                    "status": health["status"],
                    "reason": health.get("reason"),
                    "deviceMode": p.device_mode,
                    "modelCount": 0,
                    "isDefault": p.provider_id == self._settings.ai_provider_primary,
                    "isFallback": p.provider_id == self._settings.ai_provider_fallback,
                    "isDiscovered": False,
                }
            )
        # Discovered providers
        for p in self._discovered.values():
            health = await p.health_check()
            statuses.append(
                {
                    "id": p.provider_id,
                    "name": p.provider_name,
                    "status": health["status"],
                    "reason": health.get("reason"),
                    "deviceMode": p.device_mode,
                    "modelCount": len(p._endpoint.models) if hasattr(p, "_endpoint") and hasattr(p._endpoint, "models") else 0,
                    "isDefault": False,
                    "isFallback": False,
                    "isDiscovered": True,
                }
            )
        return statuses

    async def get_all_models(self) -> list[dict]:
        all_models = []
        for p in self._providers.values():
            models = await p.list_models()
            all_models.extend(models)
        # Include discovered provider models too
        for p in self._discovered.values():
            try:
                models = await p.list_models()
                all_models.extend(models)
            except Exception as exc:
                logger.debug("discovered_models_failed", provider=p.provider_id, error=str(exc))
        return all_models
