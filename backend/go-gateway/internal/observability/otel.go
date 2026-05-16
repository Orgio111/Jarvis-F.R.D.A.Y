package observability

import (
	"context"
	"fmt"
	"os"

	"go.opentelemetry.io/otel"
	"go.opentelemetry.io/otel/attribute"
	"go.opentelemetry.io/otel/exporters/otlp/otlptrace/otlptracehttp"
	"go.opentelemetry.io/otel/propagation"
	"go.opentelemetry.io/otel/sdk/resource"
	sdktrace "go.opentelemetry.io/otel/sdk/trace"
	semconv "go.opentelemetry.io/otel/semconv/v1.24.0"
	"go.opentelemetry.io/otel/trace"
)

var tracer trace.Tracer

// InitOTel initialises the OpenTelemetry trace provider with:
//   - A composite W3C TraceContext + Baggage propagator (so trace IDs flow
//     through inbound headers and outbound HTTP calls automatically).
//   - A ParentBased(TraceIDRatioBased(sampleRate)) sampler that honours parent
//     sampling decisions from upstream services. Pass 1.0 in dev, ~0.1 in prod.
//   - Resource attributes: service.name, service.version, service.environment,
//     and a best-effort host.name from $HOSTNAME.
//
// If jaegerEndpoint is empty, a no-op provider is installed and the returned
// shutdown function is a no-op. If the exporter fails to initialise, the error
// is returned but the function still installs a no-op provider so the caller
// can treat the error as non-fatal.
func InitOTel(ctx context.Context, serviceName, environment, jaegerEndpoint string, sampleRate float64) (func(context.Context) error, error) {
	// W3C propagator: always install, even when tracing is disabled, so any
	// inbound traceparent headers are still parsed (cheap, ~no overhead) and
	// downstream propagation is consistent.
	otel.SetTextMapPropagator(propagation.NewCompositeTextMapPropagator(
		propagation.TraceContext{},
		propagation.Baggage{},
	))

	if jaegerEndpoint == "" {
		otel.SetTracerProvider(sdktrace.NewTracerProvider())
		tracer = otel.Tracer(serviceName)
		return func(_ context.Context) error { return nil }, nil
	}

	// WithEndpointURL accepts a full URL (scheme + host[:port][/path]); it
	// defaults the path to /v1/traces when not given. WithEndpoint, by
	// contrast, expects bare host[:port] and we'd have to strip the scheme.
	exp, err := otlptracehttp.New(ctx,
		otlptracehttp.WithEndpointURL(jaegerEndpoint),
	)
	if err != nil {
		// Tracing is optional — install a no-op provider so the rest of the
		// app keeps working, but surface the error to the caller for logging.
		otel.SetTracerProvider(sdktrace.NewTracerProvider())
		tracer = otel.Tracer(serviceName)
		return func(_ context.Context) error { return nil },
			fmt.Errorf("otel exporter init (non-fatal): %w", err)
	}

	attrs := []attribute.KeyValue{
		semconv.ServiceName(serviceName),
		semconv.ServiceVersion("0.1.0"),
		semconv.DeploymentEnvironment(environment),
	}
	if host, herr := os.Hostname(); herr == nil && host != "" {
		attrs = append(attrs, semconv.HostName(host))
	}
	res, _ := resource.New(ctx, resource.WithAttributes(attrs...))

	tp := sdktrace.NewTracerProvider(
		sdktrace.WithBatcher(exp),
		sdktrace.WithResource(res),
		sdktrace.WithSampler(sdktrace.ParentBased(sdktrace.TraceIDRatioBased(sampleRate))),
	)

	otel.SetTracerProvider(tp)
	tracer = otel.Tracer(serviceName)

	shutdown := func(ctx context.Context) error {
		return tp.Shutdown(ctx)
	}
	return shutdown, nil
}

// Tracer returns the package-level tracer.
func Tracer() trace.Tracer {
	if tracer == nil {
		return otel.Tracer("jarvis-gateway")
	}
	return tracer
}
