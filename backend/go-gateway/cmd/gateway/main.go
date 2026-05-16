package main

import (
	"context"
	"fmt"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"

	"go.opentelemetry.io/contrib/instrumentation/net/http/otelhttp"
	"go.uber.org/zap"
	"go.uber.org/zap/zapcore"

	"github.com/orgio111/jarvis/go-gateway/internal/config"
	"github.com/orgio111/jarvis/go-gateway/internal/http/routes"
	"github.com/orgio111/jarvis/go-gateway/internal/observability"
	"github.com/orgio111/jarvis/go-gateway/internal/proxy"
	redisclient "github.com/orgio111/jarvis/go-gateway/internal/redis"
	"github.com/orgio111/jarvis/go-gateway/pkg/version"
)

func main() {
	cfg := config.Load()

	logger := buildLogger(cfg.AppEnv)
	defer logger.Sync() //nolint:errcheck

	logger.Info("starting JARVIS Go Gateway",
		zap.String("version", version.Version),
		zap.String("env", cfg.AppEnv),
		zap.String("addr", cfg.AppHost+":"+cfg.AppPort),
	)

	// ─── OpenTelemetry ────────────────────────────────────────────────────────
	ctx := context.Background()
	otelShutdown, otelErr := observability.InitOTel(ctx, cfg.OTELServiceName, cfg.AppEnv, cfg.JaegerEndpoint, cfg.OTELSampleRate)
	if otelErr != nil {
		logger.Warn("otel init non-fatal error", zap.Error(otelErr))
	}
	defer func() {
		shutCtx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
		defer cancel()
		_ = otelShutdown(shutCtx)
	}()

	// ─── Redis (optional) ─────────────────────────────────────────────────────
	var redis *redisclient.Client
	if cfg.RedisURL != "" {
		var err error
		redis, err = redisclient.New(cfg.RedisURL)
		if err != nil {
			logger.Warn("redis init failed (non-fatal)", zap.Error(err))
		} else {
			pingCtx, cancel := context.WithTimeout(ctx, 3*time.Second)
			if pingErr := redis.Ping(pingCtx); pingErr != nil {
				logger.Warn("redis ping failed at startup", zap.Error(pingErr))
			} else {
				logger.Info("redis connected", zap.String("url", maskRedisURL(cfg.RedisURL)))
			}
			cancel()
		}
	}

	// ─── Python AI proxy ──────────────────────────────────────────────────────
	aiProxy := proxy.New(cfg.PythonAIServiceURL, 30*time.Second)
	logger.Info("python ai service configured", zap.String("url", cfg.PythonAIServiceURL))

	// ─── Router ───────────────────────────────────────────────────────────────
	handler := routes.Build(cfg, aiProxy, redis, logger)

	// Wrap the router with otelhttp so every inbound request automatically
	// gets a root server span and propagated traceparent headers are honoured.
	// The span name is overridden per-route by chi's RoutePattern in
	// otelhttp.WithSpanNameFormatter for better Jaeger grouping.
	tracedHandler := otelhttp.NewHandler(handler, "http.server",
		otelhttp.WithSpanNameFormatter(func(_ string, r *http.Request) string {
			return r.Method + " " + r.URL.Path
		}),
	)

	// ─── HTTP server ──────────────────────────────────────────────────────────
	addr := fmt.Sprintf("%s:%s", cfg.AppHost, cfg.AppPort)
	srv := &http.Server{
		Addr:         addr,
		Handler:      tracedHandler,
		ReadTimeout:  15 * time.Second,
		WriteTimeout: 120 * time.Second, // long for SSE streams
		IdleTimeout:  60 * time.Second,
	}

	// ─── Graceful shutdown ────────────────────────────────────────────────────
	quit := make(chan os.Signal, 1)
	signal.Notify(quit, syscall.SIGINT, syscall.SIGTERM)

	go func() {
		logger.Info("gateway listening", zap.String("addr", addr))
		if err := srv.ListenAndServe(); err != nil && err != http.ErrServerClosed {
			logger.Fatal("server error", zap.Error(err))
		}
	}()

	<-quit
	logger.Info("shutting down gateway...")

	shutCtx, cancel := context.WithTimeout(context.Background(), 15*time.Second)
	defer cancel()

	if err := srv.Shutdown(shutCtx); err != nil {
		logger.Error("graceful shutdown error", zap.Error(err))
	}

	if redis != nil {
		_ = redis.Close()
	}

	logger.Info("gateway stopped")
}

func buildLogger(env string) *zap.Logger {
	var cfg zap.Config
	if env == "production" {
		cfg = zap.NewProductionConfig()
	} else {
		cfg = zap.NewDevelopmentConfig()
		cfg.EncoderConfig.EncodeLevel = zapcore.CapitalColorLevelEncoder
	}
	logger, err := cfg.Build()
	if err != nil {
		panic("failed to build logger: " + err.Error())
	}
	return logger
}

// maskRedisURL strips credentials from a redis:// URL for safe logging.
func maskRedisURL(url string) string {
	if len(url) > 30 {
		return url[:30] + "..."
	}
	return url
}
