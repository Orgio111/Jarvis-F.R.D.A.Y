"""OpenTelemetry tracing setup.

Initialises a TracerProvider with:
- OTLP/HTTP exporter pointing to the Jaeger collector configured via settings.
- W3C TraceContext propagator so traceparent headers from the Go gateway
  become parents of spans created here (true cross-service traces).
- ParentBased sampler that honours upstream sampling decisions.
- FastAPI auto-instrumentation so every inbound request becomes a server span.

Failure to reach the collector at startup is treated as non-fatal — tracing
silently no-ops, and the service still serves requests.
"""

from __future__ import annotations

import os
from typing import Optional

from fastapi import FastAPI
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.propagate import set_global_textmap
from opentelemetry.propagators.composite import CompositePropagator
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.trace.sampling import ParentBased, TraceIdRatioBased
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator
from opentelemetry.baggage.propagation import W3CBaggagePropagator


def init_tracing(
    app: FastAPI,
    service_name: str,
    environment: str,
    jaeger_endpoint: str,
    sample_rate: float = 1.0,
) -> None:
    """Install a TracerProvider and instrument FastAPI.

    If `jaeger_endpoint` is empty, only the propagator is installed (so
    inbound traceparent headers still parse correctly) and a no-op
    TracerProvider stays in place.
    """
    # Always install the W3C propagator — cheap, makes incoming traceparent
    # headers work even when local tracing is disabled.
    set_global_textmap(
        CompositePropagator(
            [TraceContextTextMapPropagator(), W3CBaggagePropagator()]
        )
    )

    if not jaeger_endpoint:
        return

    attrs = {
        "service.name": service_name,
        "service.version": "0.1.0",
        "deployment.environment": environment,
    }
    hostname: Optional[str] = os.environ.get("HOSTNAME")
    if hostname:
        attrs["host.name"] = hostname

    provider = TracerProvider(
        resource=Resource.create(attrs),
        sampler=ParentBased(root=TraceIdRatioBased(sample_rate)),
    )

    try:
        # OTLPSpanExporter wants the full traces endpoint. Accept either a
        # base URL like http://jaeger:4318 (append /v1/traces) or the full
        # path if the user already supplied it.
        traces_url = jaeger_endpoint.rstrip("/")
        if not traces_url.endswith("/v1/traces"):
            traces_url = f"{traces_url}/v1/traces"
        exporter = OTLPSpanExporter(endpoint=traces_url)
        provider.add_span_processor(BatchSpanProcessor(exporter))
    except Exception:
        # Exporter init failure is non-fatal — the provider stays installed
        # but spans simply have nowhere to go. Better than crashing startup.
        pass

    trace.set_tracer_provider(provider)
    FastAPIInstrumentor.instrument_app(app, tracer_provider=provider)
