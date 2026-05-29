"""BaseAgent — abstract class for all specialized agents.

Provider priority for each _chat() call:
  1. NVIDIA NIM (if nvidia_nim_api_key set)  ← new
  2. OpenRouter free models (if openrouter_api_key set)
  3. ProviderRouter fallback (existing system)

Self-prompting / agentic loop via run_agentic_loop():
  Executes up to max_iterations of: execute → reflect → re-execute
  Stops when agent signals done=True or max_iterations reached.
"""
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
        """Call best available provider. Returns (text_content, model_id_used).

        Priority: NIM (if key set) → OpenRouter free (if key set) → ProviderRouter.
        """
        from app.agents.nim_model_pool import NimModelPool
        _role = role or self.role

        # 1. Try NIM first
        if NimModelPool.available() and NimModelPool.get_model(_role, fallback_index):
            try:
                return await self._chat_nim(
                    messages, _role, fallback_index, temperature, max_tokens
                )
            except Exception as exc:
                logger.warning("nim_chat_failed_fallback", error=str(exc))

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

    # ── NVIDIA NIM chat helper ────────────────────────────────────────────────

    async def _chat_nim(
        self,
        messages: list[dict[str, str]],
        role: Optional[AgentRole] = None,
        fallback_index: int = 0,
        temperature: float = 0.2,
        max_tokens: int = 4096,
    ) -> tuple[str, str]:
        """Call NVIDIA NIM endpoint. Returns (text_content, model_id_used)."""
        from app.agents.nim_model_pool import NimModelPool
        _role = role or self.role
        model = NimModelPool.get_model(_role, fallback_index)
        if not model:
            raise RuntimeError(f"No NIM model for role={_role} fallback={fallback_index}")

        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(
                f"{NimModelPool.get_base_url()}/chat/completions",
                headers=NimModelPool.get_headers(),
                json=payload,
            )

        if resp.status_code != 200:
            if fallback_index == 0:
                logger.warning(
                    "nim_primary_failed",
                    status=resp.status_code,
                    model=model,
                )
                return await self._chat_nim(
                    messages, _role, fallback_index=1,
                    temperature=temperature, max_tokens=max_tokens,
                )
            raise RuntimeError(
                f"NIM error {resp.status_code}: {resp.text[:300]}"
            )

        data = resp.json()
        content = data["choices"][0]["message"]["content"]
        actual_model = data.get("model", model)
        return content, actual_model

    # ── Agentic loop ──────────────────────────────────────────────────────────

    async def run_agentic_loop(
        self,
        context: dict[str, Any],
        max_iterations: int = 5,
    ) -> AgentResult:
        """Self-prompting loop: execute → reflect → re-execute until done.

        Agent signals completion by returning result.data["done"] = True.
        On each iteration the previous result is appended to context["history"]
        so the agent can build on prior work.
        """
        context = dict(context)  # shallow copy — don't mutate caller's dict
        context.setdefault("history", [])
        last_result: Optional[AgentResult] = None

        for i in range(max_iterations):
            result = await self.run(context)
            last_result = result

            if not result.success:
                logger.warning(
                    "agentic_loop_agent_failed",
                    role=self.role.value,
                    iteration=i,
                    error=result.error,
                )
                break

            # Agent signals it's finished
            if result.data.get("done", True):
                logger.info(
                    "agentic_loop_done",
                    role=self.role.value,
                    iterations=i + 1,
                )
                break

            # Append result to history for next iteration
            context["history"].append(result.to_dict())
            logger.info(
                "agentic_loop_continuing",
                role=self.role.value,
                iteration=i + 1,
                remaining=max_iterations - i - 1,
            )

        return last_result or AgentResult(
            role=self.role,
            success=False,
            content="",
            error="agentic_loop produced no result",
        )

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
