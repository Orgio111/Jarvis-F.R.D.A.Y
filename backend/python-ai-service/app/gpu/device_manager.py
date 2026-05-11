from __future__ import annotations

from typing import Optional

from app.gpu.detector import GPUDetector
from app.core.logging import get_logger

logger = get_logger(__name__)


class DeviceManager:
    """
    Resolves device strings to actual device identifiers.

    Supports:
      - 'auto' resolution to the best-available CUDA device or CPU
      - explicit device strings ('cuda:0', 'cuda:1', 'cpu')
      - VRAM-aware best-device selection across all CUDA devices
    """

    @staticmethod
    def list_cuda_devices() -> list[int]:
        """Returns indices of every detected CUDA device, e.g. [0, 1]."""
        info = GPUDetector.get_info()
        if not info.cuda_available:
            return []
        return [d["index"] for d in info.devices]

    @staticmethod
    def device_free_memory_mb(index: int) -> Optional[int]:
        """
        Returns free VRAM in MB for the given CUDA device, or None if torch
        is not importable / device is invalid. Never raises.
        """
        try:
            import torch  # type: ignore

            if not torch.cuda.is_available():
                return None
            free_bytes, _total = torch.cuda.mem_get_info(index)
            return int(free_bytes // (1024 * 1024))
        except Exception as exc:
            logger.debug("device_free_memory_error", index=index, error=str(exc))
            return None

    @staticmethod
    def best_cuda_device() -> Optional[str]:
        """
        Picks the CUDA device with the most free VRAM. Returns a string like
        'cuda:1', or None if no CUDA device is usable.

        Falls back to 'cuda:0' if free-memory queries fail (torch present but
        mem_get_info errored on every device).
        """
        indices = DeviceManager.list_cuda_devices()
        if not indices:
            return None

        scored: list[tuple[int, int]] = []
        for idx in indices:
            free_mb = DeviceManager.device_free_memory_mb(idx)
            if free_mb is not None:
                scored.append((idx, free_mb))

        if not scored:
            return "cuda:0"

        best_idx, _ = max(scored, key=lambda pair: pair[1])
        return f"cuda:{best_idx}"

    @staticmethod
    def resolve(device: str, gpu_enabled: bool = True, allow_cpu_fallback: bool = True) -> str:
        """
        Resolves a requested device spec.

        - 'auto': returns the best available CUDA device when gpu_enabled, else 'cpu'.
        - 'cuda' (no index): picks the CUDA device with the most free VRAM.
        - 'cuda:N': honoured if device N exists; otherwise CPU fallback (or raise).
        - 'cpu' or anything else: returned as-is.
        """
        if device == "auto":
            if gpu_enabled and GPUDetector.is_cuda_available():
                resolved = DeviceManager.best_cuda_device() or "cpu"
                return resolved
            return "cpu"

        if device == "cuda":
            best = DeviceManager.best_cuda_device()
            if best is not None:
                return best
            if allow_cpu_fallback:
                logger.warning("device_fallback", requested=device, resolved="cpu")
                return "cpu"
            raise RuntimeError("Requested 'cuda' but no CUDA device available")

        if device.startswith("cuda:"):
            try:
                idx = int(device.split(":", 1)[1])
            except (ValueError, IndexError):
                raise RuntimeError(f"Malformed device spec: {device!r}")

            if idx in DeviceManager.list_cuda_devices():
                return device

            if allow_cpu_fallback:
                logger.warning("device_fallback", requested=device, resolved="cpu")
                return "cpu"
            raise RuntimeError(f"Requested device '{device}' unavailable and CPU fallback disabled")

        # 'cpu' or any other literal — honour as-is.
        return device

    @staticmethod
    def resolve_compute_type(compute_type: str, device: str) -> str:
        """Resolves compute_type='auto' for faster-whisper."""
        if compute_type != "auto":
            return compute_type
        if device.startswith("cuda"):
            return "float16"
        return "int8"
