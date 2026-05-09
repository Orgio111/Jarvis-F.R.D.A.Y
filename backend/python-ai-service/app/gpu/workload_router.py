from __future__ import annotations

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


class WorkloadRouter:
    """
    Maps each AI workload type to its resolved device mode.
    Reads GPU flags from settings; falls back to CPU when GPU unavailable.
    """

    def __init__(self, settings: Settings):
        self._settings = settings
        self._cuda_available = GPUDetector.is_cuda_available()
        self._workloads: dict[str, str] = {}
        self._resolve_all()

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
        logger.info("workload_routing_resolved", workloads=self._workloads)

    def get_workloads(self) -> dict[str, str]:
        return dict(self._workloads)

    def get_device_for(self, workload: str, device_spec: str = "auto") -> str:
        mode = self._workloads.get(workload, WORKLOAD_CPU)
        if mode == WORKLOAD_GPU:
            return DeviceManager.resolve(device_spec, gpu_enabled=True)
        return "cpu"

    def is_gpu_active(self) -> bool:
        return any(v == WORKLOAD_GPU for v in self._workloads.values())
