package handlers

import (
	"context"
	"net/http"
	"time"

	"github.com/orgio111/jarvis/go-gateway/internal/contracts"
	mw "github.com/orgio111/jarvis/go-gateway/internal/http/middleware"
	"github.com/orgio111/jarvis/go-gateway/internal/proxy"
	redisclient "github.com/orgio111/jarvis/go-gateway/internal/redis"
	"github.com/orgio111/jarvis/go-gateway/pkg/version"
)

// HealthHandler handles GET /api/health
type HealthHandler struct {
	aiProxy *proxy.AIProxy
	redis   *redisclient.Client
}

// NewHealthHandler creates a HealthHandler.
func NewHealthHandler(aiProxy *proxy.AIProxy, redis *redisclient.Client) *HealthHandler {
	return &HealthHandler{aiProxy: aiProxy, redis: redis}
}

// ServeHTTP handles the health check request.
func (h *HealthHandler) ServeHTTP(w http.ResponseWriter, r *http.Request) {
	correlationID := mw.GetCorrelationID(r)
	ctx := r.Context()

	checks := map[string]contracts.HealthCheck{}
	overallStatus := "pass"

	// Check Python AI service
	checks["python-ai-service"] = h.checkPythonService(ctx)
	if checks["python-ai-service"].Status == "fail" {
		overallStatus = "warn"
	}

	// Check Redis
	if h.redis != nil {
		checks["redis"] = h.checkRedis(ctx)
		if checks["redis"].Status == "fail" {
			overallStatus = "warn"
		}
	} else {
		checks["redis"] = contracts.HealthCheck{Status: "warn", Message: "Redis not configured"}
	}

	resp := contracts.HealthResponse{
		Status:    overallStatus,
		Version:   version.Version,
		Timestamp: time.Now().UTC().Format(time.RFC3339Nano),
		Checks:    checks,
	}

	contracts.WriteSuccess(w, correlationID, resp)
}

func (h *HealthHandler) checkPythonService(ctx context.Context) contracts.HealthCheck {
	ctx, cancel := context.WithTimeout(ctx, 5*time.Second)
	defer cancel()

	result, err := h.aiProxy.Get(ctx, "/health", "internal-health-check", "")
	if err != nil {
		return contracts.HealthCheck{Status: "fail", Message: "unreachable: " + err.Error()}
	}
	if !result.IsOK() {
		return contracts.HealthCheck{Status: "warn", Message: "non-200 response from python-ai-service"}
	}
	return contracts.HealthCheck{Status: "pass"}
}

func (h *HealthHandler) checkRedis(ctx context.Context) contracts.HealthCheck {
	ctx, cancel := context.WithTimeout(ctx, 3*time.Second)
	defer cancel()
	if err := h.redis.Ping(ctx); err != nil {
		return contracts.HealthCheck{Status: "fail", Message: "ping failed: " + err.Error()}
	}
	return contracts.HealthCheck{Status: "pass"}
}
