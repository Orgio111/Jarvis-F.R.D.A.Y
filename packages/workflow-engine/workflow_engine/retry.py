from __future__ import annotations

import asyncio
import time
from typing import Any, Callable

from workflow_engine.models import RetryPolicy


class RetryHandler:
    """Handles retry logic for step execution with exponential backoff."""

    async def execute_with_retry(
        self,
        coro_factory: Callable[..., Any],
        policy: RetryPolicy,
        step_id: str = "unknown",
    ) -> Any:
        """Execute a callable with retry logic."""
        last_error: Exception | None = None

        for attempt in range(policy.max_retries + 1):
            try:
                return await coro_factory()

            except asyncio.TimeoutError as exc:
                last_error = exc
                if not policy.retry_on_timeout or attempt >= policy.max_retries:
                    raise
                delay = self._backoff_delay(attempt, policy)
                await asyncio.sleep(delay)

            except Exception as exc:
                last_error = exc
                if not policy.retry_on_error:
                    raise

                # Check retryable error codes if defined
                if policy.retryable_error_codes:
                    error_code = self._extract_error_code(exc)
                    if error_code not in policy.retryable_error_codes:
                        raise

                if attempt >= policy.max_retries:
                    raise

                delay = self._backoff_delay(attempt, policy)
                await asyncio.sleep(delay)

        # Should not reach here, but just in case
        if last_error:
            raise last_error
        raise RuntimeError(f"Retry exhausted for step {step_id}")

    def _backoff_delay(self, attempt: int, policy: RetryPolicy) -> float:
        delay = policy.base_delay_ms * (policy.backoff_multiplier ** attempt)
        delay = min(delay, policy.max_delay_ms)
        return delay / 1000.0  # Convert to seconds

    @staticmethod
    def _extract_error_code(error: Exception) -> str:
        msg = str(error).lower()
        if "timeout" in msg:
            return "timeout"
        if "rate limit" in msg or "429" in msg:
            return "rate_limit"
        if "unauthorized" in msg or "401" in msg or "403" in msg:
            return "auth_error"
        if "not found" in msg or "404" in msg:
            return "not_found"
        if "server error" in msg or "500" in msg or "503" in msg:
            return "server_error"
        return "unknown_error"
