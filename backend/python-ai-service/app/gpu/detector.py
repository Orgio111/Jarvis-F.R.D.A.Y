from __future__ import annotations

import asyncio
from typing import Optional

from app.core.logging import get_logger

logger = get_logger(__name__)


class GPUInfo:
    def __init__(self):
        self.cuda_available: bool = False
        self.device_count: int = 0
        self.devices: list[dict] = []
        self.cuda_version: Optional[str] = None
        self.driver_version: Optional[str] = None
        self.torch_available: bool = False

    def to_dict(self) -> dict:
        return {
            "cudaAvailable": self.cuda_available,
            "deviceCount": self.device_count,
            "devices": self.devices,
            "cudaVersion": self.cuda_version,
            "driverVersion": self.driver_version,
            "torchAvailable": self.torch_available,
        }


class GPUDetector:
    """
    Detects GPU availability at startup.
    All torch imports are guarded — the service starts cleanly without torch.
    """

    _instance: Optional["GPUDetector"] = None
    _info: Optional[GPUInfo] = None

    @classmethod
    async def initialize(cls) -> "GPUDetector":
        detector = cls()
        await detector._detect()
        cls._instance = detector
        cls._info = detector._gpu_info
        return detector

    @classmethod
    def get_info(cls) -> GPUInfo:
        if cls._info is None:
            return GPUInfo()
        return cls._info

    @classmethod
    def is_cuda_available(cls) -> bool:
        return cls._info.cuda_available if cls._info else False

    def __init__(self):
        self._gpu_info = GPUInfo()

    async def _detect(self) -> None:
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._detect_sync)

    def _detect_sync(self) -> None:
        try:
            import torch  # type: ignore

            self._gpu_info.torch_available = True
            self._gpu_info.cuda_available = torch.cuda.is_available()

            if self._gpu_info.cuda_available:
                self._gpu_info.device_count = torch.cuda.device_count()

                for i in range(self._gpu_info.device_count):
                    props = torch.cuda.get_device_properties(i)
                    vram_bytes = props.total_memory
                    self._gpu_info.devices.append(
                        {
                            "index": i,
                            "name": torch.cuda.get_device_name(i),
                            "totalMemoryBytes": vram_bytes,
                            "totalMemoryMb": vram_bytes // (1024 * 1024),
                            "computeCapability": f"{props.major}.{props.minor}",
                        }
                    )

                # CUDA version
                try:
                    self._gpu_info.cuda_version = torch.version.cuda
                except Exception:
                    pass

            logger.info(
                "gpu_detection_complete",
                cuda_available=self._gpu_info.cuda_available,
                device_count=self._gpu_info.device_count,
                torch_version=torch.__version__,
            )

        except ImportError:
            # torch not installed — GPU not available
            logger.info("gpu_detection_skipped", reason="torch not installed")
        except Exception as exc:
            # Any other detection error — log and continue in CPU mode
            logger.warning("gpu_detection_failed", error=str(exc))
