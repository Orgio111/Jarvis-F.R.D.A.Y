"""FreeModelPool — maps agent roles to cost-free OpenRouter models.

Priority order per role:
  1. Best-quality free model for the task
  2. Fallback free model
  3. None → caller falls back to ProviderRouter

Free models confirmed on OpenRouter (as of mid-2025):
  deepseek/deepseek-chat-v3-0324:free   — 64k ctx, strong coder
  deepseek/deepseek-r1:free             — 164k ctx, chain-of-thought reasoning
  google/gemini-flash-1.5-8b            — 1M ctx, fast scan/classify (free tier)
  meta-llama/llama-3.2-3b-instruct:free — 128k ctx, fast routing/summarize
  qwen/qwen-2.5-7b-instruct:free        — 32k ctx, good summarizer
  mistralai/mistral-7b-instruct:free    — 32k ctx, general fallback
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


# role → [primary, fallback]
_ROLE_MODELS: dict[AgentRole, list[str]] = {
    AgentRole.FILE_PICKER: [
        "google/gemini-flash-1.5-8b",            # large ctx, fast
        "meta-llama/llama-3.2-3b-instruct:free",
    ],
    AgentRole.PLANNER: [
        "deepseek/deepseek-r1:free",             # reasoning
        "deepseek/deepseek-chat-v3-0324:free",
    ],
    AgentRole.EDITOR: [
        "deepseek/deepseek-chat-v3-0324:free",   # best free coder
        "qwen/qwen-2.5-7b-instruct:free",
    ],
    AgentRole.REVIEWER: [
        "deepseek/deepseek-r1:free",
        "mistralai/mistral-7b-instruct:free",
    ],
    AgentRole.TERMINAL: [
        "deepseek/deepseek-chat-v3-0324:free",   # interprets shell output
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

_OPENROUTER_BASE = "https://openrouter.ai/api/v1"


class FreeModelPool:
    """Static helper — no instance needed."""

    @staticmethod
    def get_model(role: AgentRole, fallback_index: int = 0) -> Optional[str]:
        """Return model ID for role. fallback_index=1 for secondary."""
        models = _ROLE_MODELS.get(role, [])
        if fallback_index < len(models):
            return models[fallback_index]
        return None

    @staticmethod
    def openrouter_available() -> bool:
        settings = get_settings()
        key = getattr(settings, "openrouter_api_key", None)
        return bool(key and key.strip())

    @staticmethod
    def get_base_url() -> str:
        return _OPENROUTER_BASE

    @staticmethod
    def get_headers() -> dict[str, str]:
        settings = get_settings()
        key = getattr(settings, "openrouter_api_key", "")
        return {
            "Authorization": f"Bearer {key}",
            "HTTP-Referer": "https://jarvis-local",
            "X-Title": "Jarvis-FRIDAY",
            "Content-Type": "application/json",
        }

    @staticmethod
    def all_models() -> list[str]:
        seen: list[str] = []
        for models in _ROLE_MODELS.values():
            for m in models:
                if m not in seen:
                    seen.append(m)
        return seen
