from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, AsyncIterator


class BaseProvider(ABC):
    """Abstract base for all AI providers."""

    @property
    @abstractmethod
    def provider_id(self) -> str: ...

    @property
    @abstractmethod
    def provider_name(self) -> str: ...

    @property
    @abstractmethod
    def device_mode(self) -> str:
        """Returns 'cloud', 'gpu', 'cpu', or 'disabled'."""
        ...

    @abstractmethod
    async def health_check(self) -> dict:
        """Returns {'status': 'available'|'provider_unavailable'|'error', 'reason': str|None}"""
        ...

    @abstractmethod
    async def list_models(self) -> list[dict]:
        """Returns list of model dicts. Returns [] if unavailable (no crash)."""
        ...

    @abstractmethod
    async def chat(
        self,
        messages: list[dict],
        model_id: str,
        max_tokens: int | None = None,
        **kwargs: Any,
    ) -> dict: ...

    @abstractmethod
    async def stream_chat(
        self,
        messages: list[dict],
        model_id: str,
        max_tokens: int | None = None,
        **kwargs: Any,
    ) -> AsyncIterator[str]: ...

    def is_available(self) -> bool:
        return self.device_mode != "disabled"
