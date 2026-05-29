"""ContextCompressor — prunes conversation history to stay within token budget.

Strategy:
  - Keep last 2 raw turns (user + assistant pairs) always
  - If total estimated tokens > threshold OR turns > max_turns:
      → summarize older turns into a single [system] "Prior context summary" msg
  - Uses AgentRole.SUMMARIZER (qwen-2.5-7b free) for summarization
"""
from __future__ import annotations

import re
from typing import Any

from app.core.logging import get_logger

logger = get_logger(__name__)

_DEFAULT_TOKEN_THRESHOLD = 4000   # approx tokens before compressing
_DEFAULT_MAX_TURNS = 3            # message pairs before compressing
_CHARS_PER_TOKEN = 4              # rough approximation


def _estimate_tokens(messages: list[dict[str, str]]) -> int:
    total_chars = sum(len(m.get("content", "")) for m in messages)
    return total_chars // _CHARS_PER_TOKEN


async def _summarize_messages(messages: list[dict[str, str]]) -> str:
    """Call summarizer agent to condense messages into a paragraph."""
    from app.agents.free_model_pool import AgentRole, FreeModelPool
    import httpx

    if not FreeModelPool.openrouter_available():
        # Simple truncation fallback — take last 500 chars of each message
        lines = []
        for m in messages:
            role = m.get("role", "?")
            content = m.get("content", "")[:500]
            lines.append(f"[{role}]: {content}")
        return "Prior context (truncated):\n" + "\n".join(lines)

    model = FreeModelPool.get_model(AgentRole.SUMMARIZER)
    text_block = "\n".join(
        f"[{m['role']}]: {m['content']}"
        for m in messages
    )
    payload = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are a concise summarizer. "
                    "Summarize the following conversation history into 2-4 sentences, "
                    "preserving key technical facts, decisions, and file names. "
                    "Output ONLY the summary, no preamble."
                ),
            },
            {"role": "user", "content": text_block},
        ],
        "temperature": 0.1,
        "max_tokens": 512,
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{FreeModelPool.get_base_url()}/chat/completions",
                headers=FreeModelPool.get_headers(),
                json=payload,
            )
        if resp.status_code == 200:
            return resp.json()["choices"][0]["message"]["content"].strip()
    except Exception as exc:
        logger.warning("summarize_failed", error=str(exc))

    # fallback — first 1000 chars
    return text_block[:1000] + " [truncated]"


async def compress(
    messages: list[dict[str, str]],
    token_threshold: int = _DEFAULT_TOKEN_THRESHOLD,
    max_turns: int = _DEFAULT_MAX_TURNS,
    keep_last_n: int = 2,
) -> list[dict[str, str]]:
    """Return a (possibly compressed) messages list.

    Separates system messages from conversation turns.
    Preserves all system messages. Summarizes older user/assistant turns.
    """
    if not messages:
        return messages

    # Split: system msgs stay, track conversation pairs
    system_msgs = [m for m in messages if m.get("role") == "system"]
    convo_msgs  = [m for m in messages if m.get("role") != "system"]

    # Count user/assistant pairs
    pair_count = sum(1 for m in convo_msgs if m.get("role") == "user")

    estimated_tokens = _estimate_tokens(messages)

    needs_compress = (
        estimated_tokens > token_threshold
        or pair_count > max_turns
    )

    if not needs_compress:
        return messages

    logger.info(
        "context_compressing",
        estimated_tokens=estimated_tokens,
        pair_count=pair_count,
        keep_last_n=keep_last_n,
    )

    # Keep last keep_last_n pairs (user+assistant = 2 msgs per pair)
    keep_n_msgs = keep_last_n * 2
    if len(convo_msgs) <= keep_n_msgs:
        return messages  # nothing to compress

    older   = convo_msgs[:-keep_n_msgs]
    recent  = convo_msgs[-keep_n_msgs:]

    summary_text = await _summarize_messages(older)
    summary_msg  = {
        "role": "system",
        "content": f"[Prior context summary]\n{summary_text}",
    }

    compressed = system_msgs + [summary_msg] + recent
    logger.info(
        "context_compressed",
        original_msgs=len(messages),
        compressed_msgs=len(compressed),
        saved_tokens=estimated_tokens - _estimate_tokens(compressed),
    )
    return compressed
