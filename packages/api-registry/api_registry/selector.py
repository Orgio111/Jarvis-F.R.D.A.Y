from __future__ import annotations

from typing import Literal

from api_registry.models import ApiProvider, ApiProviderStatus, ProviderProfile

SelectionStrategy = Literal["fastest", "most_reliable", "best_accuracy", "round_robin"]


class ApiProviderSelector:
    """Selects the best API provider based on runtime profiling data."""

    def __init__(self) -> None:
        self._round_robin_index: dict[str, int] = {}

    def select(
        self,
        providers: list[ApiProvider],
        strategy: SelectionStrategy = "fastest",
        required_tags: list[str] | None = None,
    ) -> ApiProvider | None:
        """Pick the best provider from a list using the given strategy."""
        available = [p for p in providers if p.status == ApiProviderStatus.ONLINE]
        if required_tags:
            available = [p for p in available if any(t in p.tags for t in required_tags)]

        if not available:
            return None

        if len(available) == 1:
            return available[0]

        if strategy == "round_robin":
            return self._round_robin(available)

        scored = [(self._score(p, strategy), p) for p in available]
        scored.sort(key=lambda x: x[0], reverse=True)
        return scored[0][1]

    def select_for_task(
        self,
        providers: list[ApiProvider],
        task_description: str,
    ) -> ApiProvider | None:
        """Context-aware selection based on task description keywords."""
        task_lower = task_description.lower()

        # Speed-critical tasks
        if any(kw in task_lower for kw in ("fast", "quick", "real-time", "live", "stream")):
            return self.select(providers, "fastest")

        # Reliability-critical tasks
        if any(kw in task_lower for kw in ("critical", "important", "payment", "order", "transaction")):
            return self.select(providers, "most_reliable")

        # Default to balanced
        return self.select(providers, "fastest")

    def _score(self, provider: ApiProvider, strategy: SelectionStrategy) -> float:
        profile = provider.profile
        if profile is None:
            return 0.5  # Neutral score for unprofiled providers

        if strategy == "fastest":
            # Lower latency = higher score
            return max(0.0, 1.0 - profile.avg_latency_ms / 3000.0) if profile.avg_latency_ms > 0 else 0.8
        elif strategy == "most_reliable":
            return profile.success_rate
        elif strategy == "best_accuracy":
            return profile.score
        else:
            return profile.score

    def _round_robin(self, providers: list[ApiProvider]) -> ApiProvider:
        # Use a group key for the round-robin group
        key = ",".join(sorted(p.name for p in providers))
        idx = self._round_robin_index.get(key, 0)
        selected = providers[idx % len(providers)]
        self._round_robin_index[key] = idx + 1
        return selected
