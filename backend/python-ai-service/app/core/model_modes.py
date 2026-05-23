"""
J.A.R.V.I.S. Model Mode System

Defines four operation modes (FAST / SMART / DEEP / CODING) that map to
model groups and preferred model IDs.  The resolver selects the best
available model for a given mode from the list of currently-discovered
models, with manual override support.

    Mode        │ Group(s)         │ Preferred model
    ────────────┼──────────────────┼────────────────────────────────
    FAST        │ fastest_chat     │ mistralai/mixtral-8x22b-instruct-v0.1
    SMART       │ deep_reasoning   │ deepseek-ai/deepseek-v4-flash
    DEEP        │ deep_reasoning   │ deepseek-ai/deepseek-v4-pro
    CODING      │ coding           │ qwen/qwen3-coder-480b-a35b-instruct
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

# ─── Mode literal ───────────────────────────────────────────────────────────────

ChatMode = Literal["fast", "smart", "deep", "coding"]
ALL_MODES: list[ChatMode] = ["fast", "smart", "deep", "coding"]

# ─── Mode metadata ─────────────────────────────────────────────────────────────

MODES_DISPLAY: dict[ChatMode, str] = {
    "fast":   "FAST MODE",
    "smart":  "SMART MODE",
    "deep":   "DEEP MODE",
    "coding": "CODING MODE",
}

MODES_DESCRIPTION: dict[ChatMode, str] = {
    "fast":   "Low-latency chat — Mixtral 8x22B",
    "smart":  "Reasoning pro — DeepSeek-V4-Flash",
    "deep":   "Maximum reasoning depth — DeepSeek-V4-Pro",
    "coding": "Code-optimised — Qwen-3-Coder 480B",
}

MODE_TO_GROUPS: dict[ChatMode, list[str]] = {
    "fast":   ["fastest_chat"],
    "smart":  ["deep_reasoning"],
    "deep":   ["deep_reasoning"],
    "coding": ["coding"],
}

MODE_PREFERRED_MODEL_KEYWORDS: dict[ChatMode, list[str]] = {
    "fast":   ["mixtral", "8x22b"],
    "smart":  ["deepseek-v4-flash", "deepseek"],
    "deep":   ["deepseek-v4-pro", "deepseek"],
    "coding": ["qwen3-coder", "480b"],
}

# ─── Resolver result ────────────────────────────────────────────────────────────


@dataclass
class ModeResolution:
    mode: ChatMode
    modelId: str
    providerId: str
    providerName: str
    modelName: str
    isManualOverride: bool = False


@dataclass
class ModeAvailability:
    mode: ChatMode
    displayName: str
    description: str
    resolved: ModeResolution | None
    availableModels: list[dict] = field(default_factory=list)


# ─── Resolver ───────────────────────────────────────────────────────────────────


def resolve_mode(
    mode: ChatMode,
    models: list[dict],
    manual_model_id: str | None = None,
    overrides: dict[str, str] | None = None,
) -> ModeResolution | None:
    """Pick the best model for *mode* from the *models* list.

    If *manual_model_id* is given, try to match it exactly first
    (manual override).  Otherwise, follow the preference order in
    MODE_PREFERRED_MODEL_KEYWORDS and fall back to the mode's group(s).

    *overrides* maps mode → exact model ID (e.g. {"smart": "deepseek-ai/deepseek-v4-flash"})
    — checked before keyword/group matching for reliability when provider
    model listings don't include the desired model.
    """
    if manual_model_id:
        exact = _find_exact(models, manual_model_id)
        if exact:
            return _to_resolution(mode, exact, is_manual_override=True)

    # 0. Config overrides (skip model listing, use exact ID)
    if overrides and mode in overrides:
        override_id = overrides[mode]
        if override_id:
            # Extract a friendly display name from the model ID
            friendly = override_id.rsplit("/", 1)[-1] if "/" in override_id else override_id
            return ModeResolution(
                mode=mode,
                modelId=override_id,
                providerId="config_override",
                providerName="Manual Override",
                modelName=friendly,
                isManualOverride=True,
            )

    # 1. Try preferred keywords
    keywords = MODE_PREFERRED_MODEL_KEYWORDS.get(mode, [])
    for kw in keywords:
        match = _find_by_keyword(models, kw)
        if match:
            return _to_resolution(mode, match)

    # 2. Fall back to group-based matching
    groups = MODE_TO_GROUPS.get(mode, [])
    for group in groups:
        candidates = [m for m in models if group in m.get("groups", [])]
        if candidates:
            return _to_resolution(mode, candidates[0])

    # 3. Last resort: any chat-capable model
    chat_models = [m for m in models if _is_chat_model(m)]
    if chat_models:
        return _to_resolution(mode, chat_models[0])

    return None


def compute_mode_availability(
    models: list[dict],
    overrides: dict[str, str] | None = None,
) -> list[ModeAvailability]:
    """Return availability info for every mode, used by the /models/modes endpoint."""
    result: list[ModeAvailability] = []
    for mode in ALL_MODES:
        groups = MODE_TO_GROUPS.get(mode, [])
        group_models = [
            m for m in models
            if any(g in m.get("groups", []) for g in groups)
        ]
        resolved = resolve_mode(mode, models, overrides=overrides)
        result.append(ModeAvailability(
            mode=mode,
            displayName=MODES_DISPLAY[mode],
            description=MODES_DESCRIPTION[mode],
            resolved=resolved,
            availableModels=group_models[:10],  # top 10
        ))
    return result


# ─── Internal helpers ───────────────────────────────────────────────────────────


def _find_exact(models: list[dict], model_id: str) -> dict | None:
    for m in models:
        if m.get("id") == model_id:
            return m
    return None


def _find_by_keyword(models: list[dict], keyword: str) -> dict | None:
    kw = keyword.lower()
    for m in models:
        mid = m.get("id", "").lower()
        mname = m.get("name", "").lower()
        if kw in mid or kw in mname:
            return m
    return None


def _to_resolution(
    mode: ChatMode,
    model: dict,
    is_manual_override: bool = False,
) -> ModeResolution:
    return ModeResolution(
        mode=mode,
        modelId=model.get("id", ""),
        providerId=model.get("providerId", ""),
        providerName=model.get("providerName", ""),
        modelName=model.get("name", ""),
        isManualOverride=is_manual_override,
    )


_EMBEDDING_KEYWORDS = ("embed", "rerank", "reranker", "bge-", "e5-", "gte-")


def _is_chat_model(model: dict) -> bool:
    mid = model.get("id", "").lower()
    return not any(kw in mid for kw in _EMBEDDING_KEYWORDS)
