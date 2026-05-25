from __future__ import annotations

from typing import Any

from api_registry.client import ExternalApiClient, ApiResponse
from api_registry.models import ApiProvider, ApiProviderStatus, ExternalApiSpec, ProviderProfile
from api_registry.normalizer import ResponseNormalizer
from api_registry.selector import ApiProviderSelector, SelectionStrategy


class ApiToolRouter:
    """Routes external API calls through the best provider with normalization."""

    def __init__(
        self,
        client: ExternalApiClient | None = None,
        selector: ApiProviderSelector | None = None,
        normalizer: ResponseNormalizer | None = None,
    ) -> None:
        self._client = client or ExternalApiClient()
        self._selector = selector or ApiProviderSelector()
        self._normalizer = normalizer or ResponseNormalizer()
        self._providers: dict[str, ApiProvider] = {}
        self._profiles: dict[str, ProviderProfile] = {}

    def register(self, provider: ApiProvider) -> None:
        """Register an external API provider."""
        self._providers[provider.name.lower()] = provider
        if provider.profile is None:
            provider.profile = ProviderProfile(name=provider.name)

    def register_many(self, providers: list[ApiProvider]) -> None:
        for p in providers:
            self.register(p)

    def get_provider(self, name: str) -> ApiProvider | None:
        return self._providers.get(name.lower())

    def list_providers(self) -> list[ApiProvider]:
        return list(self._providers.values())

    def list_available(self) -> list[ApiProvider]:
        return [p for p in self._providers.values() if p.status == ApiProviderStatus.ONLINE]

    async def call(
        self,
        endpoint_name: str,
        strategy: SelectionStrategy = "fastest",
        path_params: dict[str, str] | None = None,
        query_params: dict[str, str] | None = None,
        body: dict[str, Any] | None = None,
        auth_token: str | None = None,
        task_description: str = "",
    ) -> ApiResponse:
        """Route and execute an API call through the best matching provider."""
        candidates = self._find_providers_for_endpoint(endpoint_name)
        if not candidates:
            return ApiResponse(success=False, error=f"no_provider_for_endpoint:{endpoint_name}", status_code=404)

        if task_description:
            provider = self._selector.select_for_task(candidates, task_description)
        else:
            provider = self._selector.select(candidates, strategy)

        if provider is None:
            return ApiResponse(
                success=False, error="all_providers_unavailable", status_code=503, endpoint_name=endpoint_name,
            )

        # Find the matching endpoint spec
        spec = self._find_endpoint(provider, endpoint_name)
        if spec is None:
            return ApiResponse(
                success=False, error=f"endpoint_not_found:{endpoint_name}", status_code=404,
                provider_name=provider.name,
            )

        resp = await self._client.call(spec, path_params, query_params, body, auth_token)
        resp.provider_name = provider.name
        resp.endpoint_name = endpoint_name

        # Update runtime profile
        if provider.profile:
            if resp.success:
                provider.profile.record_success(resp.latency_ms)
            else:
                provider.profile.record_failure(resp.error or "unknown_error")

        return resp

    async def call_normalized(
        self,
        endpoint_name: str,
        strategy: SelectionStrategy = "fastest",
        expected_keys: list[str] | None = None,
        path_params: dict[str, str] | None = None,
        query_params: dict[str, str] | None = None,
        body: dict[str, Any] | None = None,
        auth_token: str | None = None,
        task_description: str = "",
    ) -> dict[str, Any]:
        """Call an API and normalize the response into a standard format."""
        resp = await self.call(
            endpoint_name, strategy, path_params, query_params, body, auth_token, task_description,
        )
        if not resp.success:
            return {"success": False, "error": resp.error, "provider": resp.provider_name}

        normalized = self._normalizer.normalize(resp.data, expected_keys=expected_keys)
        return {
            "success": True,
            "data": normalized,
            "provider": resp.provider_name,
            "latency_ms": resp.latency_ms,
            "endpoint": endpoint_name,
        }

    async def check_all_health(self) -> dict[str, ApiProviderStatus]:
        """Check health of all registered providers."""
        results: dict[str, ApiProviderStatus] = {}
        for name, provider in self._providers.items():
            status = await self._client.check_health(provider)
            provider.status = status
            results[name] = status
        return results

    async def close(self) -> None:
        await self._client.close()

    def _find_providers_for_endpoint(self, endpoint_name: str) -> list[ApiProvider]:
        """Find all providers that have an endpoint with the given name."""
        matches: list[ApiProvider] = []
        for provider in self._providers.values():
            for ep in provider.endpoints:
                if ep.name == endpoint_name or ep.path.endswith(endpoint_name):
                    matches.append(provider)
                    break
        return matches

    @staticmethod
    def _find_endpoint(provider: ApiProvider, endpoint_name: str) -> ExternalApiSpec | None:
        for ep in provider.endpoints:
            if ep.name == endpoint_name or ep.path.endswith(endpoint_name):
                return ep
        return None
