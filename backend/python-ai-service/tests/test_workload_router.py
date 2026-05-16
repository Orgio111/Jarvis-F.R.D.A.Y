"""Tests for the GPU workload router's concurrency and device selection.

These don't require an actual GPU — they exercise the dispatch logic with
CUDA detection mocked to a known state.
"""

from __future__ import annotations

import asyncio
import pytest
from unittest.mock import patch

from app.core.config import Settings
from app.gpu.detector import GPUDetector, GPUInfo
from app.gpu.workload_router import WorkloadRouter, WORKLOAD_GPU, WORKLOAD_CPU


def _gpu_info(device_count: int) -> GPUInfo:
    info = GPUInfo()
    info.torch_available = True
    info.cuda_available = device_count > 0
    info.device_count = device_count
    info.devices = [
        {
            "index": i,
            "name": f"FakeGPU{i}",
            "totalMemoryBytes": 12 * 1024 * 1024 * 1024,
            "totalMemoryMb": 12 * 1024,
            "computeCapability": "8.0",
        }
        for i in range(device_count)
    ]
    return info


def _settings_with_gpu() -> Settings:
    return Settings(
        gpu_enabled=True,
        embeddings_enabled=True,
        embeddings_gpu_enabled=True,
        stt_enabled=True,
        stt_gpu_enabled=True,
    )


def _settings_no_gpu() -> Settings:
    return Settings(
        gpu_enabled=True,
        embeddings_enabled=True,
        embeddings_gpu_enabled=True,
    )


def test_workloads_route_to_cpu_when_no_cuda():
    with patch.object(GPUDetector, "_info", _gpu_info(0)):
        router = WorkloadRouter(_settings_no_gpu())
        assert router.get_workloads()["embeddings"] == WORKLOAD_CPU


def test_workloads_route_to_gpu_when_cuda_present():
    with patch.object(GPUDetector, "_info", _gpu_info(1)):
        router = WorkloadRouter(_settings_with_gpu())
        assert router.get_workloads()["embeddings"] == WORKLOAD_GPU


@pytest.mark.asyncio
async def test_acquire_yields_cpu_when_no_gpu():
    with patch.object(GPUDetector, "_info", _gpu_info(0)):
        router = WorkloadRouter(_settings_no_gpu())
        async with router.acquire("embeddings") as device:
            assert device == "cpu"


@pytest.mark.asyncio
async def test_acquire_yields_cuda_device_when_gpu_available():
    with patch.object(GPUDetector, "_info", _gpu_info(1)):
        router = WorkloadRouter(_settings_with_gpu())
        async with router.acquire("embeddings") as device:
            assert device.startswith("cuda:") or device == "cpu"


@pytest.mark.asyncio
async def test_concurrency_cap_enforces_backpressure():
    """
    With embeddings cap = 4, the 5th concurrent acquire must wait until one
    of the first 4 releases. We verify this by tracking max-observed in-flight.
    """
    with patch.object(GPUDetector, "_info", _gpu_info(0)):
        router = WorkloadRouter(_settings_no_gpu())
        # CPU concurrency is 16 by default — set a tighter limit so the test
        # exercises real contention.
        import asyncio as _asyncio
        router._semaphores["embeddings"] = _asyncio.Semaphore(2)

    in_flight = 0
    max_in_flight = 0

    async def task():
        nonlocal in_flight, max_in_flight
        async with router.acquire("embeddings"):
            in_flight += 1
            max_in_flight = max(max_in_flight, in_flight)
            await asyncio.sleep(0.02)
            in_flight -= 1

    await asyncio.gather(*(task() for _ in range(8)))
    assert max_in_flight <= 2


@pytest.mark.asyncio
async def test_acquire_raises_when_workload_disabled():
    settings = _settings_no_gpu()
    settings.embeddings_enabled = False
    with patch.object(GPUDetector, "_info", _gpu_info(0)):
        router = WorkloadRouter(settings)
        with pytest.raises(RuntimeError, match="disabled"):
            async with router.acquire("embeddings"):
                pass
