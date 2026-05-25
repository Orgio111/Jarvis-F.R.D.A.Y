from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ContentType(str, Enum):
    JSON = "application/json"
    TEXT = "text/plain"
    HTML = "text/html"
    XML = "application/xml"
    FORM = "application/x-www-form-urlencoded"
    BINARY = "application/octet-stream"


class HttpMethod(str, Enum):
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    PATCH = "PATCH"
    DELETE = "DELETE"


class ApiProviderStatus(str, Enum):
    UNKNOWN = "unknown"
    ONLINE = "online"
    DEGRADED = "degraded"
    OFFLINE = "offline"


@dataclass
class ExternalApiSpec:
    """Describes a single external API endpoint."""

    name: str
    description: str
    base_url: str
    path: str
    method: HttpMethod = HttpMethod.GET
    content_type: ContentType = ContentType.JSON
    headers: dict[str, str] = field(default_factory=dict)
    query_params: dict[str, str] = field(default_factory=dict)
    request_body_schema: dict[str, Any] | None = None
    response_path: str | None = None  # JSON path to extract (e.g. "data.results")
    requires_auth: bool = False
    auth_header: str = "Authorization"
    auth_scheme: str = "Bearer"
    timeout_seconds: float = 10.0
    rate_limit_per_minute: int = 60


@dataclass
class ProviderProfile:
    """Runtime profile of an API provider — latency, reliability, accuracy."""

    name: str
    avg_latency_ms: float = 0.0
    success_rate: float = 1.0
    total_calls: int = 0
    successful_calls: int = 0
    last_error: str | None = None
    score: float = 1.0  # Composite score 0-1, updated after each call

    def record_success(self, latency_ms: float) -> None:
        self.total_calls += 1
        self.successful_calls += 1
        self.avg_latency_ms = (self.avg_latency_ms * (self.total_calls - 1) + latency_ms) / self.total_calls
        self.success_rate = self.successful_calls / self.total_calls
        self._update_score()

    def record_failure(self, error: str) -> None:
        self.total_calls += 1
        self.last_error = error
        self.success_rate = self.successful_calls / self.total_calls
        self._update_score()

    def _update_score(self) -> None:
        # Composite: 50% reliability, 30% latency, 20% call count maturity
        reliability = self.success_rate
        latency_score = max(0.0, 1.0 - self.avg_latency_ms / 5000.0) if self.avg_latency_ms > 0 else 0.5
        maturity = min(1.0, self.total_calls / 100.0)
        self.score = reliability * 0.5 + latency_score * 0.3 + maturity * 0.2


@dataclass
class ApiProvider:
    """A registered external API provider with multiple endpoints."""

    name: str
    description: str
    base_url: str
    endpoints: list[ExternalApiSpec] = field(default_factory=list)
    status: ApiProviderStatus = ApiProviderStatus.UNKNOWN
    profile: ProviderProfile | None = None
    tags: list[str] = field(default_factory=list)


@dataclass
class ApiResponse:
    """Normalized response from an external API call."""

    success: bool
    data: Any = None
    error: str | None = None
    status_code: int = 200
    latency_ms: float = 0.0
    provider_name: str = ""
    endpoint_name: str = ""
    raw_response: dict[str, Any] | None = None
