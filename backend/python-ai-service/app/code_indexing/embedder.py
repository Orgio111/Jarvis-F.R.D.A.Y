"""
Code embedder — produces vector embeddings for code chunks.

Supports multiple embedding modes:
  - local: sentence-transformers (default: all-MiniLM-L6-v2)
  - cloud: remote API via LiteLLM (OpenAI, Voyage, Cohere, etc.)

Based on Cocoindex-Code's asymmetric embedding pattern.
"""

from __future__ import annotations

import time
from typing import Any

import numpy as np

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)

_embedder_instance: Any = None
_embed_dim: int = 384  # default for all-MiniLM-L6-v2


async def load_embedder(model_name: str | None = None) -> bool:
    """Load the embedding model. Returns True on success."""
    global _embedder_instance, _embed_dim

    if _embedder_instance is not None:
        return True

    settings = get_settings()
    model = model_name or settings.embeddings_model or "sentence-transformers/all-MiniLM-L6-v2"

    try:
        from sentence_transformers import SentenceTransformer

        _embedder_instance = SentenceTransformer(model)
        _embed_dim = _embedder_instance.get_sentence_embedding_dimension()
        logger.info("code_embedder_loaded", model=model, dim=_embed_dim)
        return True
    except ImportError:
        logger.warning("sentence_transformers_not_installed",
                       hint="pip install sentence-transformers")
        return False
    except Exception as exc:
        logger.warning("code_embedder_load_failed", error=str(exc))
        return False


def is_loaded() -> bool:
    return _embedder_instance is not None


def embed_dimension() -> int:
    return _embed_dim


async def embed_chunks(
    texts: list[str],
    batch_size: int = 32,
) -> np.ndarray | None:
    """
    Embed a list of text chunks. Returns a float32 numpy array of shape (n, dim).

    Falls back gracefully if embedder not loaded.
    """
    global _embedder_instance

    if _embedder_instance is None:
        loaded = await load_embedder()
        if not loaded:
            return None

    if not texts:
        return np.zeros((0, _embed_dim), dtype=np.float32)

    result = []
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]

        # Apply WorkloadRouter semaphore if available
        try:
            from app.routers.gpu import get_workload_router
            wr = get_workload_router()
        except Exception:
            wr = None

        if wr is not None:
            async with wr.acquire("embeddings"):
                vecs = _embedder_instance.encode(
                    batch, normalize_embeddings=True, show_progress_bar=False
                ).astype(np.float32)
        else:
            vecs = _embedder_instance.encode(
                batch, normalize_embeddings=True, show_progress_bar=False
            ).astype(np.float32)

        result.append(vecs)

    return np.vstack(result) if result else np.zeros((0, _embed_dim), dtype=np.float32)


async def embed_query(query: str) -> np.ndarray | None:
    """Embed a single search query."""
    texts = [query]
    embeddings = await embed_chunks(texts, batch_size=1)
    return embeddings


def unload() -> None:
    """Free the embedder from memory."""
    global _embedder_instance
    _embedder_instance = None
    logger.info("code_embedder_unloaded")
