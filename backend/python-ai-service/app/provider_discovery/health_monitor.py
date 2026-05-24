"""
Health Monitor — continuous provider health checking with automatic failover detection.

Monitors provider latency, error rates, and availability in real-time.
Triggers automatic fallback when primary providers degrade.
"""

from __future__ import annotations

import asyncio
import time
from collections import defaultdict
from typing import Any

import httpx

from app.core.logging import get_logger

logger = get_logger(__name__)


class ProviderHealthStatus:
    """Real-time health status for a single provider."""

    def __init__(self, name: str, base_url: str):
        self.name = name
        self.base_url = base_url
        self.is_available: bool = False
        self.latency_ms: float = 0.0
        self.error_count: int = 0
        self.success_count: int = 0
        self.consecutive_failures: int = 0
        self.last_success: float = 0.0
        self.last_failure: float = 0.0
        self.last_error: str | None = None
        self.total_checks: int = 0

    @property
    def error_rate(self) -> float:
        total = self.error_count + self.success_count
        if total == 0:
            return 0.0
        return self.error_count / total

    @property
    def health_score(self) -> float:
        """Compute a 0-1 health score."""
        if not self.is_available:
            return 0.0

        score = 1.0
        # Penalize high latency
        if self.latency_ms > 1000:
            score *= 0.5
        elif self.latency_ms > 500:
            score *= 0.75

        # Penalize error rate
        score *= (1.0 - self.error_rate)

        # Bonus for consecutive successes
        if self.consecutive_failures == 0 and self.success_count > 10:
            score *= 1.1

        return max(0.0, min(1.0, score))

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "baseUrl": self.base_url,
            "isAvailable": self.is_available,
            "latencyMs": round(self.latency_ms, 1),
            "errorRate": round(self.error_rate, 3),
            "consecutiveFailures": self.consecutive_failures,
            "healthScore": round(self.health_score, 3),
            "totalChecks": self.total_checks,
            "lastSuccess": self.last_success,
            "lastFailure": self.last_failure,
        }


class HealthMonitor:
    """
    Continuous health monitor for AI providers.

    Periodically pings all registered providers and maintains real-time
    health status for automatic failover routing.
    """

    CHECK_INTERVAL = 60  # seconds between health checks
    DEGRADED_THRESHOLD = 3  # consecutive failures before marking degraded
    FAILURE_THRESHOLD = 5  # consecutive failures before marking unavailable

    def __init__(self):
        self._providers: dict[str, ProviderHealthStatus] = {}
        self._http = httpx.AsyncClient(timeout=10.0)
        self._running = False
        self._task: asyncio.Task | None = None

    def register(self, name: str, base_url: str) -> None:
        """Register a provider for health monitoring."""
        if name not in self._providers:
            self._providers[name] = ProviderHealthStatus(name, base_url)
            logger.info("health_monitor_registered", name=name)

    def register_many(self, providers: list[dict[str, str]]) -> None:
        """Register multiple providers."""
        for p in providers:
            self.register(p["name"], p["base_url"])

    async def check(self, name: str) -> ProviderHealthStatus:
        """Run a single health check on a provider."""
        status = self._providers.get(name)
        if not status:
            raise ValueError(f"Provider '{name}' not registered")

        status.total_checks += 1
        start = time.perf_counter()

        try:
            response = await self._http.get(
                f"{status.base_url}/models",
                params={"limit": 1},
                timeout=10.0,
            )

            status.latency_ms = (time.perf_counter() - start) * 1000

            if response.status_code < 500:
                status.is_available = True
                status.success_count += 1
                status.consecutive_failures = 0
                status.last_success = time.time()
            else:
                status.is_available = False
                status.error_count += 1
                status.consecutive_failures += 1
                status.last_failure = time.time()
                status.last_error = f"HTTP {response.status_code}"

        except Exception as exc:
            status.latency_ms = -1
            status.is_available = False
            status.error_count += 1
            status.consecutive_failures += 1
            status.last_failure = time.time()
            status.last_error = str(exc)[:100]

        return status

    async def check_all(self) -> list[ProviderHealthStatus]:
        """Run health checks on all registered providers."""
        tasks = [self.check(name) for name in self._providers]
        return await asyncio.gather(*tasks)

    async def start(self, interval: int | None = None) -> None:
        """Start the continuous health monitoring loop."""
        if self._running:
            return

        self._running = True
        interval = interval or self.CHECK_INTERVAL

        async def _loop():
            logger.info("health_monitor_started", interval=interval)
            while self._running:
                await self.check_all()
                await asyncio.sleep(interval)

        self._task = asyncio.create_task(_loop())

    async def stop(self) -> None:
        """Stop the health monitoring loop."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        await self._http.aclose()
        logger.info("health_monitor_stopped")

    def get_status(self, name: str) -> ProviderHealthStatus | None:
        return self._providers.get(name)

    def get_all_statuses(self) -> list[dict[str, Any]]:
        return [s.to_dict() for s in self._providers.values()]

    def get_available(self) -> list[dict[str, Any]]:
        return [s.to_dict() for s in self._providers.values() if s.is_available]

    def get_failover_candidates(self) -> list[dict[str, Any]]:
        """Get providers suitable for failover (healthy, not degraded)."""
        candidates = [
            s for s in self._providers.values()
            if s.is_available and s.health_score > 0.5
        ]
        candidates.sort(key=lambda s: s.health_score, reverse=True)
        return [s.to_dict() for s in candidates]


# Singleton
_monitor_instance: HealthMonitor | None = None


def get_health_monitor() -> HealthMonitor:
    global _monitor_instance
    if _monitor_instance is None:
        _monitor_instance = HealthMonitor()
    return _monitor_instance
