from __future__ import annotations

import asyncio
import time
from typing import Any

import httpx

from api_registry.models import (
    ApiProvider,
    ApiProviderStatus,
    ApiResponse,
    ContentType,
    ExternalApiSpec,
    HttpMethod,
    ProviderProfile,
)


class ExternalApiClient:
    """Dynamic HTTP client for calling external APIs with timeout, retry, and error handling."""

    def __init__(self, timeout_seconds: float = 15.0, max_retries: int = 2) -> None:
        self._timeout = timeout_seconds
        self._max_retries = max_retries
        self._client = httpx.AsyncClient(timeout=httpx.Timeout(timeout_seconds), follow_redirects=True)

    async def call(
        self,
        spec: ExternalApiSpec,
        path_params: dict[str, str] | None = None,
        query_params: dict[str, str] | None = None,
        body: dict[str, Any] | None = None,
        auth_token: str | None = None,
    ) -> ApiResponse:
        """Execute a single API call with retry logic."""
        url = self._build_url(spec, path_params)
        merged_params = {**spec.query_params, **(query_params or {})}
        headers = dict(spec.headers)

        if auth_token and spec.requires_auth:
            headers[spec.auth_header] = f"{spec.auth_scheme} {auth_token}"

        last_error: str | None = None
        start = time.monotonic()

        for attempt in range(self._max_retries + 1):
            try:
                resp = await self._request(spec.method, url, headers, merged_params, body)
                elapsed = (time.monotonic() - start) * 1000  # ms

                if resp.is_success:
                    data = self._extract_data(resp, spec)
                    return ApiResponse(
                        success=True,
                        data=data,
                        status_code=resp.status_code,
                        latency_ms=elapsed,
                        provider_name=spec.name,
                        endpoint_name=spec.path,
                        raw_response=resp.json() if resp.headers.get("content-type", "").startswith("application/json") else None,
                    )
                else:
                    last_error = f"HTTP {resp.status_code}: {resp.text[:200]}"
                    if attempt < self._max_retries and resp.status_code >= 500:
                        await asyncio.sleep(1.0 * (attempt + 1))

            except httpx.TimeoutException:
                last_error = "timeout"
                if attempt < self._max_retries:
                    await asyncio.sleep(1.0 * (attempt + 1))

            except httpx.RequestError as exc:
                last_error = str(exc)
                if attempt < self._max_retries:
                    await asyncio.sleep(1.0 * (attempt + 1))

        elapsed = (time.monotonic() - start) * 1000
        return ApiResponse(
            success=False,
            error=last_error or "unknown_error",
            status_code=0,
            latency_ms=elapsed,
            provider_name=spec.name,
            endpoint_name=spec.path,
        )

    async def check_health(self, provider: ApiProvider) -> ApiProviderStatus:
        """Quick health check — GET the base URL or first endpoint."""
        if not provider.endpoints:
            return ApiProviderStatus.UNKNOWN
        spec = provider.endpoints[0]
        resp = await self.call(spec)
        return ApiProviderStatus.ONLINE if resp.success else ApiProviderStatus.OFFLINE

    async def close(self) -> None:
        await self._client.aclose()

    def _build_url(self, spec: ExternalApiSpec, path_params: dict[str, str] | None) -> str:
        path = spec.path
        if path_params:
            for key, value in path_params.items():
                path = path.replace(f"{{{key}}}", value)
        return f"{spec.base_url.rstrip('/')}/{path.lstrip('/')}"

    async def _request(
        self,
        method: HttpMethod,
        url: str,
        headers: dict[str, str],
        params: dict[str, str],
        body: dict[str, Any] | None,
    ) -> httpx.Response:
        method_upper = method.value
        if method_upper == "GET":
            return await self._client.get(url, headers=headers, params=params)
        elif method_upper == "POST":
            return await self._client.post(url, headers=headers, params=params, json=body)
        elif method_upper == "PUT":
            return await self._client.put(url, headers=headers, params=params, json=body)
        elif method_upper == "PATCH":
            return await self._client.patch(url, headers=headers, params=params, json=body)
        elif method_upper == "DELETE":
            return await self._client.delete(url, headers=headers, params=params)
        else:
            raise ValueError(f"Unsupported HTTP method: {method}")

    def _extract_data(self, resp: httpx.Response, spec: ExternalApiSpec) -> Any:
        try:
            data = resp.json()
        except Exception:
            return resp.text[:5000]

        if spec.response_path:
            parts = spec.response_path.split(".")
            for part in parts:
                if isinstance(data, dict):
                    data = data.get(part)
                else:
                    return None
        return data
