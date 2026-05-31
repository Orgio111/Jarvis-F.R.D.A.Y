"""FreeModelPool — maps agent roles to cost-free LLM endpoints.

Provider priority (all OpenAI-compatible):
  1. Cerebras      — https://api.cerebras.ai/v1         (1M tokens/day, FAST)
  2. Groq          — https://api.groq.com/openai/v1     (14400 req/day)
  3. Google AI Studio — https://generativelanguage.googleapis.com/v1beta/openai
  4. OpenRouter    — https://openrouter.ai/api/v1       (50 req/day free / 1k with $10)
  5. ProviderRouter — existing fallback

Free models confirmed (mid-2025):

Cerebras:
  llama-4-scout-17b-16e-instruct  — fast, great coder
  llama-3.3-70b                   — strong general
  llama-3.1-8b                    — ultra-fast routing

Groq:
  llama-3.3-70b-versatile         — 1000 req/day
  llama-3.1-8b-instant            — 14400 req/day, routing/terminal
  meta-llama/llama-4-scout-17b-16e-preview — 14400/day
  moonshinemba/moonshine-base     — audio, not relevant

Google AI Studio:
  gemini-2.5-flash-lite-preview-06-17  — 500 req/day, huge ctx
  gemma-3-27b-it                       — 14400/day

OpenRouter (free tier):
  deepseek/deepseek-chat-v3-0324:free   — 64k ctx, strong coder
  deepseek/deepseek-r1:free             — 164k ctx, chain-of-thought
  google/gemini-flash-1.5-8b            — 1M ctx, fast scan
  meta-llama/llama-3.2-3b-instruct:free — 128k ctx, routing
  qwen/qwen-2.5-7b-instruct:free        — 32k ctx, summarizer
  mistralai/mistral-7b-instruct:free    — 32k ctx, fallback
"""
from __future__ import annotations

from enum import Enum
from typing import Optional

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class AgentRole(str, Enum):
    FILE_PICKER = "file_picker"
    PLANNER     = "planner"
    EDITOR      = "editor"
    REVIEWER    = "reviewer"
    TERMINAL    = "terminal"
    SUMMARIZER  = "summarizer"
    ROUTER      = "router"


# ── Per-provider model maps ───────────────────────────────────────────────────

_CEREBRAS_MODELS: dict[AgentRole, list[str]] = {
    AgentRole.FILE_PICKER: ["llama-3.1-8b"],
    AgentRole.PLANNER:     ["llama-3.3-70b"],
    AgentRole.EDITOR:      ["llama-4-scout-17b-16e-instruct"],
    AgentRole.REVIEWER:    ["llama-3.3-70b"],
    AgentRole.TERMINAL:    ["llama-3.1-8b"],
    AgentRole.SUMMARIZER:  ["llama-3.1-8b"],
    AgentRole.ROUTER:      ["llama-3.1-8b"],
}

_GROQ_MODELS: dict[AgentRole, list[str]] = {
    AgentRole.FILE_PICKER: ["llama-3.1-8b-instant"],
    AgentRole.PLANNER:     ["llama-3.3-70b-versatile"],
    AgentRole.EDITOR:      ["meta-llama/llama-4-scout-17b-16e-preview"],
    AgentRole.REVIEWER:    ["llama-3.3-70b-versatile"],
    AgentRole.TERMINAL:    ["llama-3.1-8b-instant"],
    AgentRole.SUMMARIZER:  ["llama-3.1-8b-instant"],
    AgentRole.ROUTER:      ["llama-3.1-8b-instant"],
}

_GOOGLE_MODELS: dict[AgentRole, list[str]] = {
    AgentRole.FILE_PICKER: ["gemini-2.5-flash-lite-preview-06-17"],
    AgentRole.PLANNER:     ["gemini-2.5-flash-lite-preview-06-17"],
    AgentRole.EDITOR:      ["gemini-2.5-flash-lite-preview-06-17"],
    AgentRole.REVIEWER:    ["gemini-2.5-flash-lite-preview-06-17"],
    AgentRole.TERMINAL:    ["gemma-3-27b-it"],
    AgentRole.SUMMARIZER:  ["gemma-3-27b-it"],
    AgentRole.ROUTER:      ["gemma-3-27b-it"],
}

# OpenRouter — legacy primary (now tertiary after Cerebras + Groq)
_OPENROUTER_MODELS: dict[AgentRole, list[str]] = {
    AgentRole.FILE_PICKER: [
        "google/gemini-flash-1.5-8b",
        "meta-llama/llama-3.2-3b-instruct:free",
    ],
    AgentRole.PLANNER: [
        "deepseek/deepseek-r1:free",
        "deepseek/deepseek-chat-v3-0324:free",
    ],
    AgentRole.EDITOR: [
        "deepseek/deepseek-chat-v3-0324:free",
        "qwen/qwen-2.5-7b-instruct:free",
    ],
    AgentRole.REVIEWER: [
        "deepseek/deepseek-r1:free",
        "mistralai/mistral-7b-instruct:free",
    ],
    AgentRole.TERMINAL: [
        "deepseek/deepseek-chat-v3-0324:free",
        "meta-llama/llama-3.2-3b-instruct:free",
    ],
    AgentRole.SUMMARIZER: [
        "qwen/qwen-2.5-7b-instruct:free",
        "meta-llama/llama-3.2-3b-instruct:free",
    ],
    AgentRole.ROUTER: [
        "meta-llama/llama-3.2-3b-instruct:free",
        "mistralai/mistral-7b-instruct:free",
    ],
}

_CEREBRAS_BASE  = "https://api.cerebras.ai/v1"
_GROQ_BASE      = "https://api.groq.com/openai/v1"
_GOOGLE_BASE    = "https://generativelanguage.googleapis.com/v1beta/openai"
_OPENROUTER_BASE = "https://openrouter.ai/api/v1"


class FreeModelPool:
    """Static helper — no instance needed.

    Exposes a provider-aware interface so BaseAgent._chat() can
    iterate through providers in order: Cerebras → Groq → Google → OpenRouter.
    """

    # ── Provider availability ─────────────────────────────────────────────────

    @staticmethod
    def cerebras_available() -> bool:
        key = getattr(get_settings(), "cerebras_api_key", None)
        return bool(key and key.strip())

    @staticmethod
    def groq_available() -> bool:
        key = getattr(get_settings(), "groq_api_key", None)
        return bool(key and key.strip())

    @staticmethod
    def google_available() -> bool:
        key = getattr(get_settings(), "google_ai_api_key", None)
        return bool(key and key.strip())

    @staticmethod
    def openrouter_available() -> bool:
        key = getattr(get_settings(), "openrouter_api_key", None)
        return bool(key and key.strip())

    # ── Model getters ─────────────────────────────────────────────────────────

    @staticmethod
    def get_model(role: AgentRole, fallback_index: int = 0) -> Optional[str]:
        """Return OpenRouter model ID (legacy helper for backward compat)."""
        models = _OPENROUTER_MODELS.get(role, [])
        return models[fallback_index] if fallback_index < len(models) else None

    @staticmethod
    def get_cerebras_model(role: AgentRole) -> Optional[str]:
        models = _CEREBRAS_MODELS.get(role, [])
        return models[0] if models else None

    @staticmethod
    def get_groq_model(role: AgentRole) -> Optional[str]:
        models = _GROQ_MODELS.get(role, [])
        return models[0] if models else None

    @staticmethod
    def get_google_model(role: AgentRole) -> Optional[str]:
        models = _GOOGLE_MODELS.get(role, [])
        return models[0] if models else None

    # ── Base URLs ─────────────────────────────────────────────────────────────

    @staticmethod
    def get_base_url() -> str:
        return _OPENROUTER_BASE

    @staticmethod
    def get_cerebras_base_url() -> str:
        return _CEREBRAS_BASE

    @staticmethod
    def get_groq_base_url() -> str:
        return _GROQ_BASE

    @staticmethod
    def get_google_base_url() -> str:
        return _GOOGLE_BASE

    # ── Auth headers ──────────────────────────────────────────────────────────

    @staticmethod
    def get_headers() -> dict[str, str]:
        key = getattr(get_settings(), "openrouter_api_key", "")
        return {
            "Authorization": f"Bearer {key}",
            "HTTP-Referer": "https://jarvis-local",
            "X-Title": "Jarvis-FRIDAY",
            "Content-Type": "application/json",
        }

    @staticmethod
    def get_cerebras_headers() -> dict[str, str]:
        key = getattr(get_settings(), "cerebras_api_key", "")
        return {
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        }

    @staticmethod
    def get_groq_headers() -> dict[str, str]:
        key = getattr(get_settings(), "groq_api_key", "")
        return {
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        }

    @staticmethod
    def get_google_headers() -> dict[str, str]:
        key = getattr(get_settings(), "google_ai_api_key", "")
        return {
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        }

    # ── Convenience: ordered provider list for _chat() ────────────────────────

    @staticmethod
    def provider_chain(role: AgentRole) -> list[dict]:
        """Return ordered list of {base_url, headers, model} to try in sequence."""
        pool = FreeModelPool
        chain = []

        if pool.cerebras_available():
            m = pool.get_cerebras_model(role)
            if m:
                chain.append({
                    "provider": "cerebras",
                    "base_url": pool.get_cerebras_base_url(),
                    "headers":  pool.get_cerebras_headers(),
                    "model":    m,
                })

        if pool.groq_available():
            m = pool.get_groq_model(role)
            if m:
                chain.append({
                    "provider": "groq",
                    "base_url": pool.get_groq_base_url(),
                    "headers":  pool.get_groq_headers(),
                    "model":    m,
                })

        if pool.google_available():
            m = pool.get_google_model(role)
            if m:
                chain.append({
                    "provider": "google_ai",
                    "base_url": pool.get_google_base_url(),
                    "headers":  pool.get_google_headers(),
                    "model":    m,
                })

        if pool.openrouter_available():
            for idx in range(2):
                m = pool.get_model(role, idx)
                if m:
                    chain.append({
                        "provider": "openrouter",
                        "base_url": pool.get_base_url(),
                        "headers":  pool.get_headers(),
                        "model":    m,
                    })

        return chain

    @staticmethod
    def all_models() -> list[str]:
        seen: list[str] = []
        for maps in (_OPENROUTER_MODELS, _CEREBRAS_MODELS, _GROQ_MODELS, _GOOGLE_MODELS):
            for models in maps.values():
                for m in models:
                    if m not in seen:
                        seen.append(m)
        return seen
