"""NimModelPool — NVIDIA NIM free endpoint model catalog + agent role mapping.

NVIDIA NIM hosted API: https://integrate.api.nvidia.com/v1
Compatible with OpenAI SDK (same interface as OpenRouter).

Free endpoint models confirmed at https://build.nvidia.com/models (Free Endpoint filter, 44 models):
  - Uses API key from settings.nvidia_nim_api_key
  - Base URL: settings.nvidia_nim_base_url (default: https://integrate.api.nvidia.com/v1)

Agent role mapping prioritizes:
  PLANNER/REVIEWER  → reasoning-strong models (nemotron-70b, deepseek-r1)
  EDITOR            → coding-optimized models (deepseek-v4-flash, llama-nemotron)
  FILE_PICKER       → fast/cheap models (llama-3.3-70b, nemotron-nano)
  TERMINAL          → instruction-following (mistral-nemo, llama-3.1-8b)
  SUMMARIZER/ROUTER → small fast models
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)


# ─── NIM Free Endpoint model catalog ─────────────────────────────────────────
# Sourced from https://build.nvidia.com/models?filters=endpoint_type%3Aendpoint_type_cloud
# Format: nim_model_id (used in API calls as the `model` param)

@dataclass
class NimModel:
    model_id: str          # used in API: "nvidia/llama-3.1-nemotron-70b-instruct"
    slug: str              # build.nvidia.com slug for UI links
    name: str              # display name
    context_length: int
    use_cases: list[str]   # coding, reasoning, chat, summarize, rag, fast
    publisher: str
    free: bool = True


NIM_FREE_MODELS: list[NimModel] = [
    # ── Reasoning / coding flagships ─────────────────────────────────────────
    NimModel(
        model_id="nvidia/llama-3.1-nemotron-70b-instruct",
        slug="nvidia/llama-3_1-nemotron-70b-instruct",
        name="Llama-3.1 Nemotron 70B Instruct",
        context_length=128_000,
        use_cases=["reasoning", "coding", "chat"],
        publisher="NVIDIA",
    ),
    NimModel(
        model_id="nvidia/nemotron-3-super-120b-a12b",
        slug="nvidia/nemotron-3-super-120b-a12b",
        name="Nemotron-3 Super 120B (MoE)",
        context_length=1_000_000,
        use_cases=["reasoning", "coding", "agentic", "planning"],
        publisher="NVIDIA",
    ),
    NimModel(
        model_id="deepseek-ai/deepseek-r1",
        slug="deepseek-ai/deepseek-r1",
        name="DeepSeek R1",
        context_length=128_000,
        use_cases=["reasoning", "coding", "planning"],
        publisher="DeepSeek AI",
    ),
    NimModel(
        model_id="deepseek-ai/deepseek-v4-flash",
        slug="deepseek-ai/deepseek-v4-flash",
        name="DeepSeek V4 Flash (284B MoE)",
        context_length=1_000_000,
        use_cases=["coding", "agentic", "fast"],
        publisher="DeepSeek AI",
    ),
    NimModel(
        model_id="z-ai/glm-5.1",
        slug="z-ai/glm-5.1",
        name="GLM-5.1 (Agentic)",
        context_length=128_000,
        use_cases=["agentic", "coding", "reasoning"],
        publisher="Z.ai",
    ),
    NimModel(
        model_id="minimaxai/minimax-m2.7",
        slug="minimaxai/minimax-m2.7",
        name="MiniMax M2.7 (230B)",
        context_length=1_000_000,
        use_cases=["coding", "reasoning", "chat"],
        publisher="MiniMax",
    ),
    NimModel(
        model_id="stepfun-ai/step-3.7-flash",
        slug="stepfun-ai/step-3.7-flash",
        name="Step-3.7 Flash (MoE reasoning)",
        context_length=256_000,
        use_cases=["reasoning", "coding", "agentic"],
        publisher="Stepfun",
    ),
    # ── Fast / general purpose ───────────────────────────────────────────────
    NimModel(
        model_id="meta/llama-3.3-70b-instruct",
        slug="meta/llama-3_3-70b-instruct",
        name="Llama-3.3 70B Instruct",
        context_length=128_000,
        use_cases=["chat", "coding", "summarize", "fast"],
        publisher="Meta",
    ),
    NimModel(
        model_id="meta/llama-3.1-8b-instruct",
        slug="meta/llama-3_1-8b-instruct",
        name="Llama-3.1 8B Instruct",
        context_length=128_000,
        use_cases=["fast", "summarize", "routing"],
        publisher="Meta",
    ),
    NimModel(
        model_id="meta/llama-3.2-3b-instruct",
        slug="meta/llama-3_2-3b-instruct",
        name="Llama-3.2 3B Instruct",
        context_length=128_000,
        use_cases=["fast", "routing", "summarize"],
        publisher="Meta",
    ),
    NimModel(
        model_id="mistralai/mistral-nemo-12b-instruct",
        slug="mistralai/mistral-nemo-12b-instruct",
        name="Mistral NeMo 12B",
        context_length=128_000,
        use_cases=["chat", "coding", "fast"],
        publisher="Mistral AI",
    ),
    NimModel(
        model_id="nvidia/nemotron-3-content-safety",
        slug="nvidia/nemotron-3-content-safety",
        name="Nemotron-3 Content Safety",
        context_length=32_000,
        use_cases=["safety"],
        publisher="NVIDIA",
    ),
    NimModel(
        model_id="google/gemma-4-31b-it",
        slug="google/gemma-4-31b-it",
        name="Gemma-4 31B IT",
        context_length=128_000,
        use_cases=["reasoning", "coding", "chat"],
        publisher="Google",
    ),
]

# ─── Agent role → NIM model priority list ────────────────────────────────────

from app.agents.free_model_pool import AgentRole

_NIM_ROLE_MAP: dict[AgentRole, list[str]] = {
    AgentRole.PLANNER: [
        "nvidia/nemotron-3-super-120b-a12b",    # 1M ctx, agentic planning
        "deepseek-ai/deepseek-r1",              # chain-of-thought
        "nvidia/llama-3.1-nemotron-70b-instruct",
    ],
    AgentRole.EDITOR: [
        "deepseek-ai/deepseek-v4-flash",        # 1M ctx, fast coder
        "nvidia/llama-3.1-nemotron-70b-instruct",
        "z-ai/glm-5.1",
    ],
    AgentRole.REVIEWER: [
        "deepseek-ai/deepseek-r1",
        "nvidia/llama-3.1-nemotron-70b-instruct",
        "stepfun-ai/step-3.7-flash",
    ],
    AgentRole.FILE_PICKER: [
        "meta/llama-3.3-70b-instruct",          # fast + large ctx
        "meta/llama-3.1-8b-instruct",
    ],
    AgentRole.TERMINAL: [
        "meta/llama-3.3-70b-instruct",
        "mistralai/mistral-nemo-12b-instruct",
    ],
    AgentRole.SUMMARIZER: [
        "meta/llama-3.1-8b-instruct",
        "meta/llama-3.2-3b-instruct",
    ],
    AgentRole.ROUTER: [
        "meta/llama-3.2-3b-instruct",
        "meta/llama-3.1-8b-instruct",
    ],
}

_NIM_BASE = "https://integrate.api.nvidia.com/v1"


class NimModelPool:
    """Static helper — mirrors FreeModelPool interface for NVIDIA NIM."""

    @staticmethod
    def available() -> bool:
        settings = get_settings()
        key = getattr(settings, "nvidia_nim_api_key", "")
        return bool(key and key.strip() and key != "replace_me")

    @staticmethod
    def get_base_url() -> str:
        try:
            return get_settings().nvidia_nim_base_url.rstrip("/")
        except Exception:
            return _NIM_BASE

    @staticmethod
    def get_headers() -> dict[str, str]:
        settings = get_settings()
        key = getattr(settings, "nvidia_nim_api_key", "")
        return {
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        }

    @staticmethod
    def get_model(role: AgentRole, fallback_index: int = 0) -> Optional[str]:
        models = _NIM_ROLE_MAP.get(role, [])
        if fallback_index < len(models):
            return models[fallback_index]
        return None

    @staticmethod
    def all_models() -> list[NimModel]:
        return NIM_FREE_MODELS

    @staticmethod
    def models_for_role(role: AgentRole) -> list[str]:
        return _NIM_ROLE_MAP.get(role, [])

    @staticmethod
    def model_info(model_id: str) -> Optional[NimModel]:
        for m in NIM_FREE_MODELS:
            if m.model_id == model_id:
                return m
        return None

    @staticmethod
    def nim_build_url(slug: str) -> str:
        return f"https://build.nvidia.com/{slug}"
