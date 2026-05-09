package observability

import (
	"context"
	"fmt"

	"go.opentelemetry.io/otel"
	"go.opentelemetry.io/otel/exporters/otlp/otlptrace/otlptracehttp"
	"go.opentelemetry.io/otel/sdk/resource"
	sdktrace "go.opentelemetry.io/otel/sdk/trace"
	semconv "go.opentelemetry.io/otel/semconv/v1.24.0"
	"go.opentelemetry.io/otel/trace"
)

var tracer trace.Tracer

// InitOTel initialises the OpenTelemetry trace provider.
// If jaegerEndpoint is empty or the exporter fails, tracing is disabled gracefully.
func InitOTel(ctx context.Context, serviceName, jaegerEndpoint string) (func(context.Context) error, error) {
	if jaegerEndpoint == "" {
		otel.SetTracerProvider(sdktrace.NewTracerProvider())
		tracer = otel.Tracer(serviceName)
		return func(_ context.Context) error { return nil }, nil
	}

	exp, err := otlptracehttp.New(ctx,
		otlptracehttp.WithEndpoint(jaegerEndpoint),
		otlptracehttp.WithInsecure(),
	)
	if err != nil {
		// Tracing is optional — do not fail startup
		otel.SetTracerProvider(sdktrace.NewTracerProvider())
		tracer = otel.Tracer(serviceName)
		return func(_ context.Context) error { return nil },
			fmt.Errorf("otel exporter init (non-fatal): %w", err)
	}

	res, _ := resource.New(ctx,
		resource.WithAttributes(
			semconv.ServiceName(serviceName),
			semconv.ServiceVersion("0.1.0"),
		),
	)

	tp := sdktrace.NewTracerProvider(
		sdktrace.WithBatcher(exp),
		sdktrace.WithResource(res),
		sdktrace.WithSampler(sdktrace.AlwaysSample()),
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
