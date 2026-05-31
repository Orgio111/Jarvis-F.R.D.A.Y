"""
FAISS GPU Index — GPU-accelerated vector search wrapper.

Wraps faiss.GpuIndexFlatIP for fast GPU-accelerated nearest-neighbour search:
  - Uses faiss.StandardGpuResources for GPU memory management
  - Transparent CPU fallback if CUDA/FAISS is unavailable
  - Supports incremental addition and search
  - Persists to disk via faiss.write_index/read_index

Usage:
    idx = FaissGpuIndex(dim=384, device=0)
    idx.add(vectors)          # vectors: np.ndarray (N, dim)
    distances, indices = idx.search(query_vector, k=5)
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

import numpy as np

from app.core.logging import get_logger

logger = get_logger(__name__)


class FaissGpuIndex:
    """
    GPU-accelerated FAISS index (GpuIndexFlatIP) with CPU fallback.

    On GPU, uses GpuIndexFlatIP with StandardGpuResources for optimal
    memory management on the default CUDA device.

    Falls back to IndexFlatIP on CPU when:
      - torch/CUDA is unavailable
      - faiss-gpu is not installed (uses faiss-cpu instead)
      - GPU memory allocation fails
    """

    def __init__(
        self,
        dim: int = 384,
        device: int = 0,
        gpu_enabled: bool = True,
        index_path: str | Path | None = None,
    ):
        self._dim = dim
        self._device = device
        self._gpu_enabled = gpu_enabled
        self._index_path = Path(index_path) if index_path else None
        self._index: Any = None
        self._gpu_resources: Any = None
        self._using_gpu = False
        self._initialized = False
        self._build_count = 0

    # ── Lifecycle ────────────────────────────────────────────────────────────

    def initialize(self) -> bool:
        """
        Create or load the index. Attempts GPU first, falls back to CPU.

        Returns True if the index is usable (GPU or CPU).
        """
        if self._initialized:
            return True

        # Try loading from disk first
        if self._index_path and self._index_path.exists():
            try:
                import faiss  # type: ignore
                self._index = faiss.read_index(str(self._index_path))
                self._dim = self._index.d
                self._initialized = True
                logger.info(
                    "faiss_gpu_index_loaded",
                    path=str(self._index_path),
                    vectors=self._index.ntotal,
                    dim=self._dim,
                )
                return True
            except Exception as exc:
                logger.warning(
                    "faiss_gpu_index_load_failed",
                    error=str(exc),
                    path=str(self._index_path),
                )

        # Create fresh index — try GPU first
        if self._gpu_enabled:
            self._using_gpu = self._try_init_gpu()

        if not self._using_gpu:
            self._using_gpu = False
            self._try_init_cpu()

        self._initialized = self._index is not None
        if self._initialized:
            mode = "gpu" if self._using_gpu else "cpu"
            logger.info(
                "faiss_index_created",
                mode=mode,
                dim=self._dim,
            )
        else:
            logger.warning("faiss_index_creation_failed", dim=self._dim)

        return self._initialized

    def _try_init_gpu(self) -> bool:
        """Attempt to create a GPU FAISS index. Returns True on success."""
        try:
            import faiss  # type: ignore

            # Check CUDA availability via PyTorch
            try:
                import torch  # type: ignore
                if not torch.cuda.is_available():
                    logger.info("faiss_gpu_no_cuda_using_cpu")
                    return False
            except ImportError:
                return False

            # Create GPU resources
            self._gpu_resources = faiss.StandardGpuResources()
            # Use temporary memory of 512 MB for GPU index operations
            self._gpu_resources.setTempMemory(512 * 1024 * 1024)

            config = faiss.GpuIndexFlatConfig()
            config.device = self._device
            config.useFloat16CoarseQuantizer = False  # full precision for IP
            config.storeTransposed = False

            self._index = faiss.GpuIndexFlatIP(
                self._gpu_resources, self._dim, config
            )
            logger.info(
                "faiss_gpu_index_initialized",
                device=self._device,
                dim=self._dim,
            )
            return True

        except Exception as exc:
            logger.warning(
                "faiss_gpu_index_init_failed",
                error=str(exc),
                fallback="cpu",
            )
            return False

    def _try_init_cpu(self) -> None:
        """Create a CPU FAISS index (IndexFlatIP)."""
        try:
            import faiss  # type: ignore
            self._index = faiss.IndexFlatIP(self._dim)
            logger.info("faiss_cpu_index_initialized", dim=self._dim)
        except Exception as exc:
            logger.warning("faiss_cpu_index_init_failed", error=str(exc))

    @property
    def is_available(self) -> bool:
        return self._initialized and self._index is not None

    @property
    def size(self) -> int:
        return self._index.ntotal if self._index is not None else 0

    @property
    def mode(self) -> str:
        if not self._initialized:
            return "unavailable"
        return "gpu" if self._using_gpu else "cpu"

    # ── Core API ─────────────────────────────────────────────────────────────

    def add(self, vectors: np.ndarray) -> int:
        """
        Add vectors to the index.

        Args:
            vectors: numpy array of shape (N, dim), float32, normalized.

        Returns:
            Number of vectors added.
        """
        if self._index is None:
            return 0

        if vectors.shape[0] == 0:
            return 0

        if vectors.shape[1] != self._dim:
            logger.warning(
                "faiss_dim_mismatch",
                expected=self._dim,
                got=vectors.shape[1],
            )
            return 0

        try:
            self._index.add(vectors.astype(np.float32))
            self._build_count += 1
            self._persist()
            return vectors.shape[0]
        except Exception as exc:
            logger.warning("faiss_add_failed", error=str(exc))
            return 0

    def search(
        self,
        query_vector: np.ndarray,
        k: int = 10,
    ) -> tuple[np.ndarray, np.ndarray]:
        """
        Search the index for nearest neighbours.

        Args:
            query_vector: numpy array of shape (1, dim) or (N, dim), float32.
            k: number of nearest neighbours to return.

        Returns:
            (distances, indices) — each shape (N, k).
            indices of -1 mean fewer than k results available.
        """
        if self._index is None or self._index.ntotal == 0:
            empty_d = np.array([[]], dtype=np.float32)
            empty_i = np.array([[]], dtype=np.int64)
            return empty_d, empty_i

        k = min(k, self._index.ntotal)
        try:
            distances, indices = self._index.search(
                query_vector.astype(np.float32), k
            )
            return distances, indices
        except Exception as exc:
            logger.warning("faiss_search_failed", error=str(exc))
            empty_d = np.array([[]], dtype=np.float32)
            empty_i = np.array([[]], dtype=np.int64)
            return empty_d, empty_i

    def reset(self) -> None:
        """Clear the index and free memory."""
        if self._index is not None:
            self._index.reset()
            self._build_count = 0
            logger.info("faiss_index_reset")

    # ─── Persistence ─────────────────────────────────────────────────────────

    def _persist(self) -> None:
        """Write index to disk (fire-and-forget)."""
        if self._index_path is None or self._index is None:
            return
        try:
            import faiss  # type: ignore
            self._index_path.parent.mkdir(parents=True, exist_ok=True)
            faiss.write_index(self._index, str(self._index_path))
            logger.debug("faiss_index_persisted", path=str(self._index_path))
        except Exception as exc:
            logger.debug("faiss_index_persist_failed", error=str(exc))

    def persist_now(self) -> None:
        """Force index persistence to disk."""
        self._persist()

    # ── Stats ────────────────────────────────────────────────────────────────

    def stats(self) -> dict[str, Any]:
        return {
            "available": self.is_available,
            "mode": self.mode,
            "dimension": self._dim,
            "vectors": self.size,
            "device": self._device,
            "gpuEnabled": self._gpu_enabled,
            "buildCount": self._build_count,
            "indexPath": str(self._index_path) if self._index_path else None,
        }

    def __del__(self):
        """Cleanup GPU resources on deletion."""
        self._gpu_resources = None
        self._index = None
