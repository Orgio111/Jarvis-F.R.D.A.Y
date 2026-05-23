"""
Base Sector Brain — abstract interface for all specialized cognitive layers.

Every sector brain:
  - Has a unique identifier and display name
  - Receives tasks from the Macro Brain
  - Processes tasks using domain-specific system prompts
  - Returns structured results with confidence scores
  - Can spawn sub-execution agents
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4


@dataclass
class SectorBrainResult:
    """Structured output from a sector brain's processing."""

    success: bool
    output: str
    confidence: float = 0.0  # 0.0 to 1.0
    reasoning: str = ""
    suggestions: list[str] = field(default_factory=list)
    actions_taken: list[dict] = field(default_factory=list)
    elapsed_ms: float = 0.0
    error: str | None = None
    brain_id: str = ""
    brain_name: str = ""


class BaseSectorBrain(ABC):
    """Abstract base for all sector brains."""

    # Override in subclasses
    SECTOR_ID: str = "base"
    BRAIN_NAME: str = "Base Brain"
    DESCRIPTION: str = "Abstract base sector brain"
    CAPABILITIES: list[str] = []

    @classmethod
    def get_brain_id(cls) -> str:
        return cls.SECTOR_ID

    @classmethod
    def get_brain_name(cls) -> str:
        return cls.BRAIN_NAME

    @classmethod
    def get_brain_description(cls) -> str:
        return cls.DESCRIPTION

    @classmethod
    def get_capabilities(cls) -> list[str]:
        return cls.CAPABILITIES

    def __init__(self, provider=None):
        self._provider = provider

    @abstractmethod
    def get_system_prompt(self, context: str = "") -> str:
        """Return the domain-specific system prompt for this brain."""
        ...

    async def process(
        self,
        task: str,
        context: str = "",
        max_tokens: int = 1024,
    ) -> SectorBrainResult:
        """Process a task using this sector brain's domain expertise.

        Subclasses can override this for custom processing logic.
        The default implementation sends the task to the LLM provider
        using the brain's specialized system prompt.
        """
        import time
        start = time.perf_counter()

        try:
            from app.providers.router import ProviderRouter
            pr = ProviderRouter.get()
            provider = self._provider or pr.get_active_provider()

            if provider is None:
                return SectorBrainResult(
                    success=False,
                    output="",
                    error="No AI provider available",
                    brain_id=self.SECTOR_ID,
                    brain_name=self.BRAIN_NAME,
                )

            system_prompt = self.get_system_prompt(context)
            user_prompt = f"Task: {task}\n\nContext: {context[:1200] if context else 'None'}"

            result = await provider.chat(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                model_id="",
                max_tokens=max_tokens,
            )

            content = (
                result.get("choices", [{}])[0]
                .get("message", {})
                .get("content", "")
            )

            elapsed = round((time.perf_counter() - start) * 1000, 1)

            return SectorBrainResult(
                success=True,
                output=content,
                confidence=0.85,
                reasoning=f"Processed by {self.BRAIN_NAME}",
                elapsed_ms=elapsed,
                brain_id=self.SECTOR_ID,
                brain_name=self.BRAIN_NAME,
            )

        except Exception as exc:
            elapsed = round((time.perf_counter() - start) * 1000, 1)
            return SectorBrainResult(
                success=False,
                output="",
                error=str(exc),
                confidence=0.0,
                brain_id=self.SECTOR_ID,
                brain_name=self.BRAIN_NAME,
                elapsed_ms=elapsed,
            )
