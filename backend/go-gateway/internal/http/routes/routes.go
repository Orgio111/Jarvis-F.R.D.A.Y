package routes

import (
	"net/http"

	"github.com/go-chi/chi/v5"
	chimw "github.com/go-chi/chi/v5/middleware"
	"go.uber.org/zap"

	"github.com/orgio111/jarvis/go-gateway/internal/config"
	"github.com/orgio111/jarvis/go-gateway/internal/contracts"
	"github.com/orgio111/jarvis/go-gateway/internal/http/handlers"
	mw "github.com/orgio111/jarvis/go-gateway/internal/http/middleware"
	"github.com/orgio111/jarvis/go-gateway/internal/observability"
	"github.com/orgio111/jarvis/go-gateway/internal/proxy"
	redisclient "github.com/orgio111/jarvis/go-gateway/internal/redis"
)

// Build constructs and returns the complete chi router for the gateway.
func Build(cfg *config.Config, aiProxy *proxy.AIProxy, redis *redisclient.Client, logger *zap.Logger) http.Handler {
	r := chi.NewRouter()

	// ─── Global middleware ────────────────────────────────────────────────────
	r.Use(mw.Recovery(logger))
	r.Use(mw.CORS(cfg.CORSAllowedOrigins))
	r.Use(mw.Correlation)
	r.Use(mw.RateLimiter(cfg.RateLimitPerMinute))
	r.Use(chimw.Compress(5))

	// ─── Prometheus metrics (no auth) ─────────────────────────────────────────
	r.Handle("/metrics", observability.MetricsHandler())

	// ─── Health (no session / client-version headers required) ───────────────
	healthH := handlers.NewHealthHandler(aiProxy, redis)
	r.Get("/api/health", healthH.ServeHTTP)

	// ─── All feature routes require the 3 canonical headers ──────────────────
	r.Group(func(r chi.Router) {
		r.Use(mw.Session)
		r.Use(mw.ClientVersion)
		r.Use(mw.RequestLogger(logger))

		// Bootstrap
		bootstrapH := handlers.NewBootstrapHandler(cfg, aiProxy)
		r.Get("/api/bootstrap", bootstrapH.ServeHTTP)

		// System
		systemH := handlers.NewSystemHandler(cfg, aiProxy)
		r.Get("/api/system/status", systemH.Status)
		r.Get("/api/system/metrics", systemH.Metrics)
		r.Get("/api/monitoring/metrics", systemH.Metrics)

		// GPU
		gpuH := handlers.NewGPUHandler(cfg, aiProxy)
		r.Get("/api/gpu/status", gpuH.Status)
		r.Get("/api/gpu/metrics", gpuH.Metrics)
		r.Get("/api/gpu/workloads", gpuH.Workloads)
		r.Get("/api/gpu/events/stream", gpuH.EventsStream)
		r.Post("/api/gpu/workloads/reload", gpuH.ReloadWorkloads)
		r.Patch("/api/gpu/settings", gpuH.PatchSettings)

		// Providers
		providersH := handlers.NewProvidersHandler(cfg, aiProxy)
		r.Get("/api/providers", providersH.List)
		r.Get("/api/providers/{providerId}", providersH.Get)

		// Models
		modelsH := handlers.NewModelsHandler(cfg, aiProxy)
		r.Get("/api/models", modelsH.List)

		// Chat
		chatH := handlers.NewChatHandler(cfg, aiProxy)
		r.Post("/api/chat/completions", chatH.Completions)
		r.Get("/api/chat/history", chatH.History)

		// 404 with canonical envelope
		r.NotFound(func(w http.ResponseWriter, r *http.Request) {
			contracts.WriteNotFound(w, mw.GetCorrelationID(r))
		})
	})

	return r
}
