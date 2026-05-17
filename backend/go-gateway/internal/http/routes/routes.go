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

	// ─── Bootstrap (public; no session required) ─────────────────────────────
	bootstrapH := handlers.NewBootstrapHandler(cfg, aiProxy)
	r.Get("/api/bootstrap", bootstrapH.ServeHTTP)

	// ─── All feature routes require the 3 canonical headers ──────────────────
	r.Group(func(r chi.Router) {
		r.Use(mw.Session)
		r.Use(mw.ClientVersion)
		r.Use(mw.RequestLogger(logger))

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

		// Voice
		voiceH := handlers.NewVoiceHandler(cfg, aiProxy)
		r.Get("/api/voice/status", voiceH.Status)
		r.Post("/api/voice/stt", voiceH.STT)
		r.Post("/api/voice/tts", voiceH.TTS)

		// Memory
		memoryH := handlers.NewMemoryHandler(cfg, aiProxy)
		r.Get("/api/memory/status", memoryH.Status)
		r.Post("/api/memory/search", memoryH.Search)
		r.Post("/api/memory/store", memoryH.Store)
		r.Delete("/api/memory/clear", memoryH.Clear)

		// Execution
		executionH := handlers.NewExecutionHandler(cfg, aiProxy)
		r.Get("/api/execution/status", executionH.Status)
		r.Post("/api/execution/run", executionH.Run)

		// Tools
		toolsH := handlers.NewToolsHandler(cfg, aiProxy)
		r.Get("/api/tools", toolsH.List)
		r.Post("/api/tools/{toolId}/execute", toolsH.Execute)

		// Search
		searchH := handlers.NewSearchHandler(cfg, aiProxy)
		r.Get("/api/search/status", searchH.Status)
		r.Post("/api/search", searchH.Search)

		// Vision
		visionH := handlers.NewVisionHandler(cfg, aiProxy)
		r.Get("/api/vision/status", visionH.Status)
		r.Post("/api/vision/analyze", visionH.Analyze)

		// Self-improvement
		selfImpH := handlers.NewSelfImprovementHandler(cfg, aiProxy)
		r.Get("/api/self-improvement/status", selfImpH.Status)
		r.Get("/api/self-improvement/suggestions", selfImpH.ListSuggestions)
		r.Post("/api/self-improvement/suggest", selfImpH.Suggest)
		r.Post("/api/self-improvement/suggestions/{suggestionId}/approve", selfImpH.Approve)
		r.Post("/api/self-improvement/suggestions/{suggestionId}/reject", selfImpH.Reject)

		// Local actions
		localActH := handlers.NewLocalActionsHandler(cfg, aiProxy)
		r.Get("/api/local-actions", localActH.List)
		r.Get("/api/local-actions/pending", localActH.ListPending)
		r.Post("/api/local-actions/{actionId}/execute", localActH.Execute)
		r.Post("/api/local-actions/approvals/{approvalId}/approve", localActH.Approve)
		r.Post("/api/local-actions/approvals/{approvalId}/deny", localActH.Deny)

		// 404 with canonical envelope
		r.NotFound(func(w http.ResponseWriter, r *http.Request) {
			contracts.WriteNotFound(w, mw.GetCorrelationID(r))
		})
	})

	// ─── WebSocket events (no session headers required — protocol upgrade) ────
	eventsH := handlers.NewEventsHandler(cfg)
	r.Get("/ws/events/{topic}", eventsH.Stream)

	return r
}
