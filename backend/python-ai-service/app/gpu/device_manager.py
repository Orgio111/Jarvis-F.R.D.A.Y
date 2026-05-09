from __future__ import annotations

from app.gpu.detector import GPUDetector
from app.core.logging import get_logger

logger = get_logger(__name__)


class DeviceManager:
    """
    Resolves 'auto' device strings to actual device identifiers.
    Used by all GPU-capable workloads to pick cuda:0 or cpu.
    """

    @staticmethod
    def resolve(device: str, gpu_enabled: bool = True, allow_cpu_fallback: bool = True) -> str:
        """
        Returns 'cuda:0' (or specific device) if GPU is available and enabled,
        otherwise returns 'cpu'.
        """
        if device != "auto":
            # Explicit device requested — honour it if valid
            if device.startswith("cuda"):
                if GPUDetector.is_cuda_available():
                    return device
                if allow_cpu_fallback:
                    logger.warning("device_fallback", requested=device, resolved="cpu")
                    return "cpu"
                raise RuntimeError(f"Requested device '{device}' unavailable and CPU fallback disabled")
            return device

        # Auto resolution
        if gpu_enabled and GPUDetector.is_cuda_available():
            return "cuda:0"
        return "cpu"

    @staticmethod
    def resolve_compute_type(compute_type: str, device: str) -> str:
        """Resolves compute_type='auto' for faster-whisper."""
        if compute_type != "auto":
            return compute_type
        if device.startswith("cuda"):
            return "float16"
        return "int8"
