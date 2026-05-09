package handlers

import (
	"context"
	"encoding/json"
	"net/http"
	"time"

	"github.com/orgio111/jarvis/go-gateway/internal/config"
	"github.com/orgio111/jarvis/go-gateway/internal/contracts"
	mw "github.com/orgio111/jarvis/go-gateway/internal/http/middleware"
	"github.com/orgio111/jarvis/go-gateway/internal/proxy"
	"github.com/orgio111/jarvis/go-gateway/pkg/version"
)

// SystemHandler handles /api/system/* endpoints
type SystemHandler struct {
	cfg       *config.Config
	aiProxy   *proxy.AIProxy
	startedAt time.Time
}

// NewSystemHandler creates a SystemHandler.
func NewSystemHandler(cfg *config.Config, aiProxy *proxy.AIProxy) *SystemHandler {
	return &SystemHandler{
		cfg:       cfg,
		aiProxy:   aiProxy,
		startedAt: time.Now(),
	}
}

// Status handles GET /api/system/status
func (h *SystemHandler) Status(w http.ResponseWriter, r *http.Request) {
	correlationID := mw.GetCorrelationID(r)
	ctx := r.Context()

	status, err := h.fetchStatusFromPython(ctx, correlationID)
	if err != nil {
		// Return gateway-level status when Python is unavailable
		status = h.localStatus("degraded")
	}

	contracts.WriteSuccess(w, correlationID, status)
}

// Metrics handles GET /api/system/metrics
func (h *SystemHandler) Metrics(w http.ResponseWriter, r *http.Request) {
	correlationID := mw.GetCorrelationID(r)
	ctx := r.Context()

	metrics, err := h.fetchMetricsFromPython(ctx, correlationID)
	if err != nil {
		// Return zeroed metrics when Python is unavailable
		metrics = contracts.SystemMetrics{
			Timestamp: time.Now().UTC().Format(time.RFC3339Nano),
		}
	}

	contracts.WriteSuccess(w, correlationID, metrics)
}

func (h *SystemHandler) fetchStatusFromPython(ctx context.Context, correlationID string) (contracts.SystemStatus, error) {
	ctx, cancel := context.WithTimeout(ctx, 5*time.Second)
	defer cancel()

	result, err := h.aiProxy.Get(ctx, "/system/status", correlationID, "")
	if err != nil {
		return contracts.SystemStatus{}, err
	}
	if !result.IsOK() {
		return contracts.SystemStatus{}, errServiceError("python-ai-service")
	}

	var envelope struct {
		Ok   bool                   `json:"ok"`
		Data contracts.SystemStatus `json:"data"`
	}
	if err := json.Unmarshal(result.Body, &envelope); err != nil {
		return contracts.SystemStatus{}, err
	}
	return envelope.Data, nil
}

func (h *SystemHandler) fetchMetricsFromPython(ctx context.Context, correlationID string) (contracts.SystemMetrics, error) {
	ctx, cancel := context.WithTimeout(ctx, 5*time.Second)
	defer cancel()

	result, err := h.aiProxy.Get(ctx, "/system/metrics", correlationID, "")
	if err != nil {
		return contracts.SystemMetrics{}, err
	}
	if !result.IsOK() {
		return contracts.SystemMetrics{}, errServiceError("python-ai-service")
	}

	var envelope struct {
		Ok   bool                    `json:"ok"`
		Data contracts.SystemMetrics `json:"data"`
	}
	if err := json.Unmarshal(result.Body, &envelope); err != nil {
		return contracts.SystemMetrics{}, err
	}
	return envelope.Data, nil
}

func (h *SystemHandler) localStatus(status string) contracts.SystemStatus {
	return contracts.SystemStatus{
		Status:    status,
		Version:   version.Version,
		AppEnv:    h.cfg.AppEnv,
		Uptime:    formatUptime(time.Since(h.startedAt)),
		StartedAt: h.startedAt.UTC().Format(time.RFC3339Nano),
		Components: map[string]contracts.CompStatus{
			"gateway": {Name: "go-gateway", Status: "ok"},
			"python-ai-service": {Name: "python-ai-service", Status: "down", Message: "unreachable"},
		},
	}
}
