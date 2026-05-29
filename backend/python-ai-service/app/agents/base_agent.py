"""BaseAgent — abstract class for all specialized agents."""
from __future__ import annotations

import json
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Optional

import httpx

from app.agents.free_model_pool import AgentRole, FreeModelPool
from app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class AgentResult:
    role: AgentRole
    success: bool
    content: str                        # main textual output
    data: dict[str, Any] = field(default_factory=dict)   # structured payload
    model_used: str = ""
    elapsed_ms: float = 0.0
    error: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "role": self.role.value,
            "success": self.success,
            "content": self.content,
            "data": self.data,
            "model_used": self.model_used,
            "elapsed_ms": round(self.elapsed_ms, 1),
            "error": self.error,
        }


class BaseAgent(ABC):
    """All specialized agents extend this."""

    role: AgentRole          # must set in subclass

    def __init__(self, timeout: float = 60.0):
        self.timeout = timeout
        self._http: Optional[httpx.AsyncClient] = None

    # ── Public entry point ────────────────────────────────────────────────────

    async def run(self, context: dict[str, Any]) -> AgentResult:
        """Validate → execute → wrap result."""
        t0 = time.perf_counter()
        try:
            result = await self._execute(context)
            result.elapsed_ms = (time.perf_counter() - t0) * 1000
            logger.info(
                "agent_complete",
                role=self.role.value,
                success=result.success,
                elapsed_ms=result.elapsed_ms,
                model=result.model_used,
            )
            return result
        except Exception as exc:
            elapsed = (time.perf_counter() - t0) * 1000
            logger.error("agent_error", role=self.role.value, error=str(exc))
            return AgentResult(
                role=self.role,
                success=False,
                content="",
                error=str(exc),
                elapsed_ms=elapsed,
            )

    # ── Subclass contract ─────────────────────────────────────────────────────

    @abstractmethod
    async def _execute(self, context: dict[str, Any]) -> AgentResult:
        """Core logic — implement in every subclass."""

    # ── OpenRouter chat helper ────────────────────────────────────────────────

    async def _chat(
        self,
        messages: list[dict[str, str]],
        role: Optional[AgentRole] = None,
        fallback_index: int = 0,
        temperature: float = 0.2,
        max_tokens: int = 4096,
    ) -> tuple[str, str]:
        """Call OpenRouter. Returns (text_content, model_id_used).

        Falls back to ProviderRouter if OpenRouter key is absent.
        """
        _role = role or self.role
        model = FreeModelPool.get_model(_role, fallback_index)

        if not FreeModelPool.openrouter_available() or not model:
            return await self._chat_via_provider(messages, max_tokens)

        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(
                f"{FreeModelPool.get_base_url()}/chat/completions",
                headers=FreeModelPool.get_headers(),
                json=payload,
            )

        if resp.status_code != 200:
            # Try secondary model once
            if fallback_index == 0:
                logger.warning(
                    "openrouter_primary_failed",
                    status=resp.status_code,
                    model=model,
                )
                return await self._chat(
                    messages, _role, fallback_index=1,
                    temperature=temperature, max_tokens=max_tokens,
                )
            raise RuntimeError(
                f"OpenRouter error {resp.status_code}: {resp.text[:300]}"
            )

        data = resp.json()
        content = data["choices"][0]["message"]["content"]
        actual_model = data.get("model", model)
        return content, actual_model

    async def _chat_via_provider(
        self,
        messages: list[dict[str, str]],
        max_tokens: int = 4096,
    ) -> tuple[str, str]:
        """Fallback: use existing ProviderRouter."""
        from app.providers.router import ProviderRouter
        provider = ProviderRouter.get().get_active_provider()
        if provider is None:
            raise RuntimeError("No provider available and OpenRouter key not set.")
        result = await provider.chat(messages, max_tokens=max_tokens)
        model = getattr(provider, "model", "unknown")
        return result, model

    # ── JSON extraction helper ────────────────────────────────────────────────

    @staticmethod
    def _extract_json(text: str) -> Any:
        """Extract first JSON object/array from text."""
        # Try raw parse first
        stripped = text.strip()
        try:
            return json.loads(stripped)
        except json.JSONDecodeError:
            pass
        # Strip markdown code fences
        for fence in ("```json", "```"):
            if fence in stripped:
                start = stripped.index(fence) + len(fence)
                end = stripped.rindex("```", start) if "```" in stripped[start:] else len(stripped)
                try:
                    return json.loads(stripped[start:end].strip())
                except json.JSONDecodeError:
                    pass
        # Find first { or [
        for start_char, end_char in (("{", "}"), ("[", "]")):
            s = stripped.find(start_char)
            e = stripped.rfind(end_char)
            if s != -1 and e > s:
                try:
                    return json.loads(stripped[s:e+1])
                except json.JSONDecodeError:
                    pass
        raise ValueError(f"No valid JSON found in: {stripped[:200]}")
