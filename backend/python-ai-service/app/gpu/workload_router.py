from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from typing import AsyncIterator

from app.core.config import Settings
from app.gpu.detector import GPUDetector
from app.gpu.device_manager import DeviceManager
from app.core.logging import get_logger

logger = get_logger(__name__)

# Workload device literals
WORKLOAD_GPU = "gpu"
WORKLOAD_CPU = "cpu"
WORKLOAD_CLOUD = "cloud"
WORKLOAD_DISABLED = "disabled"

# Per-workload concurrency caps. Keeps each model from being hit by N
# requests at once, which is the #1 cause of GPU OOM under load. Cloud and
# CPU workloads tolerate more concurrency than GPU because they don't share
# scarce VRAM.
DEFAULT_GPU_CONCURRENCY: dict[str, int] = {
    "localLlm": 1,        # large model, sequential per-instance
    "stt": 2,             # whisper batches small
    "tts": 2,
    "embeddings": 4,      # batch-friendly
    "faiss": 8,           # search is fast
    "vision": 2,
    "rag": 4,
    "memorySynthesis": 1, # background, low priority
}

# CPU/cloud paths are bounded mainly to protect the FastAPI event loop from
# being swamped, not by hardware contention.
DEFAULT_CPU_CONCURRENCY = 16


class WorkloadRouter:
    """
    Maps each AI workload type to its resolved device mode and provides an
    async acquire() context manager that:

      - holds a per-workload semaphore so concurrent calls don't OOM the GPU,
      - picks the actual CUDA device (multi-GPU, VRAM-aware),
      - logs queue waits for observability.
    """

    def __init__(self, settings: Settings):
        self._settings = settings
        self._cuda_available = GPUDetector.is_cuda_available()
        self._workloads: dict[str, str] = {}
        self._semaphores: dict[str, asyncio.Semaphore] = {}
        self._cuda_devices = DeviceManager.list_cuda_devices()
        self._rr_counter = 0
        self._rr_lock = asyncio.Lock()
        self._resolve_all()
        self._init_semaphores()

    # ─── Resolution ──────────────────────────────────────────────────────────

    def _resolve_workload(self, enabled: bool, gpu_flag: bool) -> str:
        if not enabled:
            return WORKLOAD_DISABLED
        if gpu_flag and self._cuda_available and self._settings.gpu_enabled:
            return WORKLOAD_GPU
        return WORKLOAD_CPU

    def _resolve_all(self) -> None:
        s = self._settings
        self._workloads = {
            "localLlm": self._resolve_workload(s.local_llm_enabled, s.local_llm_gpu_enabled),
            "stt": self._resolve_workload(s.stt_enabled, s.stt_gpu_enabled),
            "tts": self._resolve_workload(s.tts_enabled, s.tts_gpu_enabled == "true" or s.tts_gpu_enabled == "auto"),
            "embeddings": self._resolve_workload(s.embeddings_enabled, s.embeddings_gpu_enabled),
            "faiss": self._resolve_workload(s.faiss_enabled, s.faiss_gpu_enabled),
            "vision": self._resolve_workload(s.vision_enabled, s.vision_gpu_enabled),
            "rag": self._resolve_workload(True, s.rag_gpu_acceleration_enabled),
            "memorySynthesis": self._resolve_workload(True, s.memory_synthesis_gpu_enabled),
        }
        logger.info(
            "workload_routing_resolved",
            workloads=self._workloads,
            cuda_devices=self._cuda_devices,
        )

    def _init_semaphores(self) -> None:
        for workload, mode in self._workloads.items():
            if mode == WORKLOAD_DISABLED:
                continue
            if mode == WORKLOAD_GPU:
                limit = DEFAULT_GPU_CONCURRENCY.get(workload, 1)
            else:
                limit = DEFAULT_CPU_CONCURRENCY
            self._semaphores[workload] = asyncio.Semaphore(limit)

    # ─── Public API ──────────────────────────────────────────────────────────

    def get_workloads(self) -> dict[str, str]:
        return dict(self._workloads)

    def get_device_for(self, workload: str, device_spec: str = "auto") -> str:
        """
        Synchronous device lookup — no concurrency control. Use acquire()
        for actual inference; this is for status/metrics paths.
        """
        mode = self._workloads.get(workload, WORKLOAD_CPU)
        if mode == WORKLOAD_GPU:
            return DeviceManager.resolve(device_spec, gpu_enabled=True)
        return "cpu"

    def is_gpu_active(self) -> bool:
        return any(v == WORKLOAD_GPU for v in self._workloads.values())

    @asynccontextmanager
    async def acquire(self, workload: str) -> AsyncIterator[str]:
        """
        Reserve an inference slot for `workload` and yield the resolved
        device string. Blocks (with backpressure) if the workload is already
        at its concurrency cap.

        Usage:
            async with router.acquire("embeddings") as device:
                model.run(text, device=device)
        """
        mode = self._workloads.get(workload, WORKLOAD_CPU)
        if mode == WORKLOAD_DISABLED:
            raise RuntimeError(f"Workload {workload!r} is disabled")

        sem = self._semaphores.get(workload)
        if sem is None:
            device = await self._pick_device(mode)
            yield device
            return

        if sem.locked():
            logger.info("workload_queue_wait", workload=workload, mode=mode)

        async with sem:
            device = await self._pick_device(mode)
            yield device

    # ─── Internals ───────────────────────────────────────────────────────────

    async def _pick_device(self, mode: str) -> str:
        if mode != WORKLOAD_GPU:
            return "cpu"

        if not self._cuda_devices:
            return "cpu"

        # Single-GPU fast path.
        if len(self._cuda_devices) == 1:
            return f"cuda:{self._cuda_devices[0]}"

        # Multi-GPU: prefer the device with the most free VRAM right now.
        # Fall back to round-robin if mem_get_info isn't available.
        best = DeviceManager.best_cuda_device()
        if best is not None:
            return best

        async with self._rr_lock:
            idx = self._cuda_devices[self._rr_counter % len(self._cuda_devices)]
            self._rr_counter += 1
        return f"cuda:{idx}"
