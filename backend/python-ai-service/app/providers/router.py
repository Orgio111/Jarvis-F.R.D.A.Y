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


class ProviderRouter:
    """
    Selects the right provider for a given request.
    If the primary provider is unavailable, falls back to secondary.
    """

    _instance: "ProviderRouter | None" = None

    def __init__(self, settings: Settings):
        self._settings = settings
        self._providers: dict[str, "BaseProvider"] = {}
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

    def get_provider(self, provider_id: str) -> "BaseProvider | None":
        return self._providers.get(provider_id)

    def get_active_provider(self) -> "BaseProvider | None":
        providers = self.get_providers_in_priority_order()
        return providers[0] if providers else None

    def get_providers_in_priority_order(self) -> "list[BaseProvider]":
        """Returns available providers in priority order (primary first, fallback second)."""
        mode = self._settings.ai_provider_routing_mode
        primary_id = self._settings.ai_provider_primary
        fallback_id = self._settings.ai_provider_fallback

        if mode == "primary":
            p = self._providers.get(primary_id)
            return [p] if p and p.is_available() else []

        if mode == "fallback":
            p = self._providers.get(fallback_id)
            return [p] if p and p.is_available() else []

        # auto: primary first, then fallback
        result: list[BaseProvider] = []
        primary = self._providers.get(primary_id)
        if primary and primary.is_available():
            result.append(primary)
        fallback = self._providers.get(fallback_id)
        if fallback and fallback.is_available():
            result.append(fallback)
        return result

    def get_all_providers(self) -> list["BaseProvider"]:
        return list(self._providers.values())

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
                }
            )
        return statuses

    async def get_all_models(self) -> list[dict]:
        all_models = []
        for p in self._providers.values():
            models = await p.list_models()
            all_models.extend(models)
        return all_models
