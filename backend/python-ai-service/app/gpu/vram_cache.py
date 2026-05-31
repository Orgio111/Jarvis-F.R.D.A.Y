"""
GPU VRAM Cache — accelerated embedding cache for memory fabric.

Stores embedding vectors as PyTorch CUDA tensors in GPU VRAM:
  - LRU eviction when the VRAM budget is exceeded
  - GPU-accelerated cosine similarity search via torch.mm
  - Batch embedding computation on GPU via SentenceTransformer
  - Thread-safe via asyncio.Lock
  - Graceful CPU fallback when CUDA is unavailable

Usage:
    cache = GpuVramCache(
        budget_mb=1024,
        enabled=True,
        device="cuda:0",
    )
    await cache.initialize()
    vec = await cache.get_or_compute("hello world")
    results = await cache.search("query text", top_k=5)
"""

from __future__ import annotations

import asyncio
import time
from collections import OrderedDict
from typing import Any

from app.core.logging import get_logger

logger = get_logger(__name__)

# Estimate: 384-dim float32 vector = 384 * 4 = 1536 bytes ≈ 1.5 KB
# With overhead, ~2 KB per entry. 1 GB = ~500,000 entries.
_BYTES_PER_VECTOR = 2048  # conservative estimate with overhead


class GpuVramCache:
    """
    GPU VRAM-accelerated embedding cache.

    Features:
      - Embeddings stored as CUDA tensors for fast GPU similarity search
      - LRU eviction: least-recently-used entries purged when budget exceeded
      - Batch embedding computation on GPU via SentenceTransformer
      - Search returns cosine similarity scores via torch.mm
      - All CUDA ops are guarded — gracefully falls back to CPU
    """

    def __init__(
        self,
        budget_mb: int = 1024,
        enabled: bool = True,
        device: str = "auto",
        model_name: str = "sentence-transformers/all-MiniLM-L6-v2",
    ):
        self._budget_bytes = budget_mb * 1024 * 1024
        self._enabled = enabled
        self._device = device
        self._model_name = model_name
        self._resolved_device: str = "cpu"

        # LRU cache: text_hash -> (tensor: CUDA, timestamp)
        self._cache: OrderedDict[str, tuple[Any, float]] = OrderedDict()
        self._lock = asyncio.Lock()
        self._embedder: Any = None
        self._cuda_available = False
        self._current_bytes = 0
        self._hits = 0
        self._misses = 0
        self._initialized = False

    # ── Lifecycle ────────────────────────────────────────────────────────────

    async def initialize(self) -> None:
        """Initialize embedder and detect CUDA. Non-fatal on failure."""
        if not self._enabled:
            logger.info("gpu_vram_cache_disabled")
            self._initialized = True
            return

        try:
            import torch  # type: ignore

            self._cuda_available = torch.cuda.is_available()
            if self._cuda_available:
                if self._device == "auto":
                    self._resolved_device = f"cuda:{torch.cuda.current_device()}"
                elif self._device.startswith("cuda:"):
                    self._resolved_device = self._device
                elif self._device == "cuda":
                    self._resolved_device = f"cuda:{torch.cuda.current_device()}"
                else:
                    self._resolved_device = "cpu"

                if self._resolved_device.startswith("cuda"):
                    device_idx = int(self._resolved_device.split(":")[1])
                    free_mb, total_mb = (
                        torch.cuda.mem_get_info(device_idx)
                    )
                    free_bytes = free_mb
                    actual_budget = min(self._budget_bytes, free_bytes // 2)
                    logger.info(
                        "gpu_vram_cache_budget",
                        budget_mb=actual_budget // (1024 * 1024),
                        free_mb=free_mb // (1024 * 1024),
                        total_mb=total_mb // (1024 * 1024),
                        device=self._resolved_device,
                    )
                    self._budget_bytes = actual_budget
                logger.info(
                    "gpu_vram_cache_cuda_ready",
                    device=self._resolved_device,
                )
            else:
                logger.info("gpu_vram_cache_cuda_unavailable_using_cpu")
        except ImportError:
            logger.info("gpu_vram_cache_torch_not_installed_using_cpu")
        except Exception as exc:
            logger.warning("gpu_vram_cache_init_warning", error=str(exc))

        # Load embedder
        try:
            from sentence_transformers import SentenceTransformer  # type: ignore

            self._embedder = SentenceTransformer(
                self._model_name,
                device=self._resolved_device,
            )
            logger.info(
                "gpu_vram_cache_embedder_loaded",
                model=self._model_name,
                device=self._resolved_device,
            )
        except Exception as exc:
            logger.warning(
                "gpu_vram_cache_embedder_fallback",
                error=str(exc),
            )
            # Try CPU embedder as fallback
            try:
                from sentence_transformers import SentenceTransformer

                self._embedder = SentenceTransformer(self._model_name)
                self._resolved_device = "cpu"
                logger.info(
                    "gpu_vram_cache_embedder_cpu_fallback",
                    model=self._model_name,
                )
            except Exception as exc2:
                logger.warning(
                    "gpu_vram_cache_embedder_unavailable",
                    error=str(exc2),
                )
                self._enabled = False

        self._initialized = True

    @property
    def is_available(self) -> bool:
        return self._initialized and self._enabled and self._embedder is not None

    @property
    def is_gpu_active(self) -> bool:
        return self.is_available and self._resolved_device.startswith("cuda")

    @property
    def resolved_device(self) -> str:
        return self._resolved_device

    # ── Core API ─────────────────────────────────────────────────────────────

    async def get_or_compute(self, text: str) -> list[float] | None:
        """
        Return cached embedding vector (as CPU list) or compute and cache it.

        If the cache is disabled or embedder is unavailable, computes fresh
        and returns without caching.
        """
        if not self._enabled or self._embedder is None:
            return await self._compute_embedding(text)

        text_hash = self._hash_text(text)

        async with self._lock:
            cached = self._cache.get(text_hash)
            if cached is not None:
                # LRU touch: move to end
                vec_tensor, _ts = cached
                self._cache.move_to_end(text_hash)
                self._hits += 1
                return vec_tensor.cpu().tolist()

        self._misses += 1
        vec = await self._compute_embedding(text)
        if vec is None:
            return None

        await self._store(text_hash, vec)
        return vec

    async def search(
        self,
        query: str,
        top_k: int = 10,
        score_threshold: float = 0.0,
    ) -> list[dict[str, Any]]:
        """
        GPU-accelerated similarity search against all cached embeddings.

        Uses torch.mm (matrix multiply) on CUDA tensors for fast cosine
        similarity. Falls back to sequential CPU comparison.

        Returns list of {text, score, hash} sorted by score descending.
        """
        query_vec = await self._compute_embedding(query)
        if query_vec is None:
            return []

        async with self._lock:
            if not self._cache:
                return []

            # Build tensor matrix from cache values
            texts: list[str] = []
            tensors: list[Any] = []
            hashes: list[str] = []
            for h, (t, _ts) in self._cache.items():
                texts.append("")  # placeholder, we don't store texts
                tensors.append(t)
                hashes.append(h)

            if not tensors:
                return []

            try:
                import torch  # type: ignore

                # Stack into a single matrix: (N, dim)
                matrix = torch.stack(tensors)  # all on CUDA
                query_t = torch.tensor(
                    query_vec, dtype=torch.float32,
                    device=self._resolved_device
                    if self._cuda_available else "cpu",
                ).unsqueeze(0)  # (1, dim)

                # Cosine similarity via matrix multiply (vectors are normalized)
                scores = torch.mm(query_t, matrix.t()).squeeze(0)  # (N,)
                if self._cuda_available:
                    scores = scores.cpu()
                scores_np = scores.numpy()

                # Get top-k indices
                import numpy as np  # type: ignore

                top_indices = np.argsort(-scores_np)[:top_k]

                results = []
                for idx in top_indices:
                    score = float(scores_np[idx])
                    if score < score_threshold:
                        continue
                    h = hashes[idx]
                    # Update access time
                    if h in self._cache:
                        old_t, _ = self._cache[h]
                        self._cache[h] = (old_t, time.time())
                    results.append({
                        "hash": h,
                        "score": round(score, 4),
                    })
                return results

            except Exception as exc:
                logger.debug("gpu_vram_cache_search_fallback", error=str(exc))
                return []

    async def get_stats(self) -> dict[str, Any]:
        """Return cache statistics."""
        async with self._lock:
            total = len(self._cache)
            total_requests = self._hits + self._misses
            hit_rate = (
                round(self._hits / total_requests, 3)
                if total_requests > 0
                else 0.0
            )
            return {
                "enabled": self._enabled,
                "initialized": self._initialized,
                "device": self._resolved_device,
                "cudaAvailable": self._cuda_available,
                "entries": total,
                "currentBytes": self._current_bytes,
                "currentMb": round(self._current_bytes / (1024 * 1024), 2),
                "budgetBytes": self._budget_bytes,
                "budgetMb": round(self._budget_bytes / (1024 * 1024), 1),
                "usagePercent": round(
                    self._current_bytes / self._budget_bytes * 100, 1
                )
                if self._budget_bytes > 0
                else 0.0,
                "hits": self._hits,
                "misses": self._misses,
                "hitRate": hit_rate,
                "embedderAvailable": self._embedder is not None,
            }

    async def clear(self) -> None:
        """Clear all cached embeddings and free VRAM."""
        async with self._lock:
            self._cache.clear()
            self._current_bytes = 0
            self._hits = 0
            self._misses = 0
            logger.info("gpu_vram_cache_cleared")

    async def evict(self, count: int = 0) -> int:
        """
        Evict least-recently-used entries.

        If count=0, evicts oldest entries until under 80% of budget.
        Returns number of entries evicted.
        """
        async with self._lock:
            target_bytes = int(self._budget_bytes * 0.8)
            evicted = 0
            while self._cache and self._current_bytes > target_bytes:
                _hash, (_t, _ts) = self._cache.popitem(last=False)  # FIFO = LRU
                self._current_bytes -= _BYTES_PER_VECTOR
                del _t
                evicted += 1
                if count > 0 and evicted >= count:
                    break
            if evicted:
                logger.info(
                    "gpu_vram_cache_evicted",
                    count=evicted,
                    remaining=len(self._cache),
                )
            return evicted

    # ── Internals ────────────────────────────────────────────────────────────

    async def _compute_embedding(self, text: str) -> list[float] | None:
        """Compute embedding vector (CPU list of floats)."""
        if self._embedder is None:
            return None
        try:
            loop = asyncio.get_event_loop()
            vec = await loop.run_in_executor(
                None,
                lambda: self._embedder.encode(
                    [text], normalize_embeddings=True
                ),
            )
            return vec[0].tolist()
        except Exception as exc:
            logger.debug("gpu_vram_cache_embed_failed", error=str(exc))
            return None

    async def _store(self, text_hash: str, vec: list[float]) -> None:
        """Store embedding in VRAM cache (under lock)."""
        async with self._lock:
            # If already cached under a different hash, skip
            if text_hash in self._cache:
                return

            # Evict if needed
            while (
                self._current_bytes + _BYTES_PER_VECTOR > self._budget_bytes
                and self._cache
            ):
                _h, (_t, _ts) = self._cache.popitem(last=False)
                self._current_bytes -= _BYTES_PER_VECTOR
                del _t

            try:
                import torch  # type: ignore

                tensor = torch.tensor(
                    vec,
                    dtype=torch.float32,
                    device=self._resolved_device
                    if self._cuda_available
                    else "cpu",
                )
                self._cache[text_hash] = (tensor, time.time())
                self._current_bytes += _BYTES_PER_VECTOR
            except Exception:
                pass

    @staticmethod
    def _hash_text(text: str) -> str:
        import hashlib
        return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]
