from __future__ import annotations

from typing import Any, Literal

from app.core.config import Settings
from app.core.logging import get_logger

logger = get_logger(__name__)

SelectionStrategy = Literal["fastest", "most_reliable", "best_accuracy", "round_robin"]


class ApiRegistryService:
    """Singleton service wrapping the external API registry router for the JARVIS backend."""

    _instance: ApiRegistryService | None = None

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._initialized = False
        self._router: Any = None

    @classmethod
    def initialize(cls, settings: Settings) -> ApiRegistryService:
        instance = cls(settings)
        cls._instance = instance
        # Lazy-init to avoid import issues at module level
        return instance

    @classmethod
    def get(cls) -> ApiRegistryService:
        if cls._instance is None:
            raise RuntimeError("ApiRegistryService not initialized")
        return cls._instance

    async def _ensure_router(self) -> Any:
        if self._router is not None:
            return self._router
        from api_registry.router import ApiToolRouter
        from api_registry.client import ExternalApiClient
        from api_registry.selector import ApiProviderSelector
        from api_registry.normalizer import ResponseNormalizer

        client = ExternalApiClient(timeout_seconds=15.0, max_retries=2)
        selector = ApiProviderSelector()
        normalizer = ResponseNormalizer()
        self._router = ApiToolRouter(client=client, selector=selector, normalizer=normalizer)

        # Register built-in external APIs
        await self._register_default_apis()

        logger.info("api_registry_service_initialized")
        return self._router

    async def _register_default_apis(self) -> None:
        """Register common public APIs as built-in providers."""
        from api_registry.models import ApiProvider, ApiProviderStatus, ExternalApiSpec, HttpMethod

        # Weather API
        weather = ApiProvider(
            name="OpenWeatherMap",
            description="Free weather data and forecasts",
            base_url="https://api.openweathermap.org",
            status=ApiProviderStatus.UNKNOWN,
            tags=["weather", "data", "free"],
            endpoints=[
                ExternalApiSpec(
                    name="current_weather",
                    description="Get current weather by city",
                    path="/data/2.5/weather",
                    method=HttpMethod.GET,
                    query_params={"units": "metric"},
                    response_path="main",
                    timeout_seconds=8.0,
                    rate_limit_per_minute=60,
                ),
                ExternalApiSpec(
                    name="forecast",
                    description="5-day weather forecast",
                    path="/data/2.5/forecast",
                    method=HttpMethod.GET,
                    query_params={"units": "metric"},
                    response_path="list",
                    timeout_seconds=10.0,
                    rate_limit_per_minute=60,
                ),
            ],
        )
        self._router.register(weather)

        # Crypto API
        crypto = ApiProvider(
            name="CoinGecko",
            description="Free cryptocurrency prices and market data",
            base_url="https://api.coingecko.com/api/v3",
            status=ApiProviderStatus.UNKNOWN,
            tags=["crypto", "finance", "free"],
            endpoints=[
                ExternalApiSpec(
                    name="crypto_price",
                    description="Get current price of a cryptocurrency",
                    path="/simple/price",
                    method=HttpMethod.GET,
                    response_path=None,
                    timeout_seconds=8.0,
                    rate_limit_per_minute=30,
                ),
                ExternalApiSpec(
                    name="crypto_trending",
                    description="Top trending cryptocurrencies",
                    path="/search/trending",
                    method=HttpMethod.GET,
                    response_path="coins",
                    timeout_seconds=8.0,
                    rate_limit_per_minute=30,
                ),
            ],
        )
        self._router.register(crypto)

        # News API
        news = ApiProvider(
            name="NewsAPI",
            description="Headlines and news articles from around the world",
            base_url="https://newsapi.org/v2",
            status=ApiProviderStatus.UNKNOWN,
            tags=["news", "headlines", "free"],
            endpoints=[
                ExternalApiSpec(
                    name="top_headlines",
                    description="Top headlines by country or category",
                    path="/top-headlines",
                    method=HttpMethod.GET,
                    response_path="articles",
                    requires_auth=True,
                    timeout_seconds=8.0,
                    rate_limit_per_minute=100,
                ),
                ExternalApiSpec(
                    name="everything",
                    description="Search all articles by keyword",
                    path="/everything",
                    method=HttpMethod.GET,
                    response_path="articles",
                    requires_auth=True,
                    timeout_seconds=10.0,
                    rate_limit_per_minute=100,
                ),
            ],
        )
        self._router.register(news)

    async def list_providers(self) -> list[dict]:
        router = await self._ensure_router()
        return [
            {
                "name": p.name,
                "description": p.description,
                "status": p.status.value,
                "endpointCount": len(p.endpoints),
                "tags": p.tags,
                "score": round(p.profile.score, 3) if p.profile else 0.5,
            }
            for p in router.list_providers()
        ]

    async def call_api(
        self,
        endpoint_name: str,
        strategy: SelectionStrategy = "fastest",
        path_params: dict[str, str] | None = None,
        query_params: dict[str, str] | None = None,
        body: dict[str, Any] | None = None,
        auth_token: str | None = None,
        task_description: str = "",
    ) -> dict:
        router = await self._ensure_router()
        result = await router.call_normalized(
            endpoint_name=endpoint_name,
            strategy=strategy,
            path_params=path_params,
            query_params=query_params,
            body=body,
            auth_token=auth_token,
            task_description=task_description,
        )
        return result

    async def check_health(self) -> dict[str, str]:
        router = await self._ensure_router()
        statuses = await router.check_all_health()
        return {name: status.value for name, status in statuses.items()}

    async def close(self) -> None:
        if self._router is not None:
            await self._router.close()
