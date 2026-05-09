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
	"github.com/orgio111/jarvis/go-gateway/internal/streaming"
)

// GPUHandler handles /api/gpu/* endpoints
type GPUHandler struct {
	cfg     *config.Config
	aiProxy *proxy.AIProxy
}

// NewGPUHandler creates a GPUHandler.
func NewGPUHandler(cfg *config.Config, aiProxy *proxy.AIProxy) *GPUHandler {
	return &GPUHandler{cfg: cfg, aiProxy: aiProxy}
}

// Status handles GET /api/gpu/status
func (h *GPUHandler) Status(w http.ResponseWriter, r *http.Request) {
	correlationID := mw.GetCorrelationID(r)
	ctx := r.Context()

	status, err := h.fetchStatusFromPython(ctx, correlationID)
	if err != nil {
		// Python unavailable — return CPU fallback status
		status = contracts.CPUFallbackGPUStatus(h.cfg.GPURequired)
	}

	contracts.WriteSuccess(w, correlationID, status)
}

// Metrics handles GET /api/gpu/metrics
func (h *GPUHandler) Metrics(w http.ResponseWriter, r *http.Request) {
	correlationID := mw.GetCorrelationID(r)
	ctx := r.Context()

	metrics, err := h.fetchMetricsFromPython(ctx, correlationID, "/gpu/metrics")
	if err != nil {
		metrics = []contracts.GPUMetrics{}
	}

	contracts.WriteSuccess(w, correlationID, metrics)
}

// Workloads handles GET /api/gpu/workloads
func (h *GPUHandler) Workloads(w http.ResponseWriter, r *http.Request) {
	correlationID := mw.GetCorrelationID(r)
	ctx := r.Context()

	status, err := h.fetchStatusFromPython(ctx, correlationID)
	if err != nil {
		status = contracts.CPUFallbackGPUStatus(h.cfg.GPURequired)
	}

	contracts.WriteSuccess(w, correlationID, status.Workloads)
}

// EventsStream handles GET /api/gpu/events/stream — SSE
func (h *GPUHandler) EventsStream(w http.ResponseWriter, r *http.Request) {
	sse := streaming.NewSSEWriter(w)
	if sse == nil {
		http.Error(w, "streaming not supported", http.StatusInternalServerError)
		return
	}

	correlationID := mw.GetCorrelationID(r)
	ctx := r.Context()

	// Send initial GPU status as first event
	status, err := h.fetchStatusFromPython(ctx, correlationID)
	if err != nil {
		status = contracts.CPUFallbackGPUStatus(h.cfg.GPURequired)
	}

	evt := contracts.NewBackendEvent(contracts.EventGPUStatusChanged, correlationID, nil, nil, status)
	_ = sse.WriteEvent(contracts.EventGPUStatusChanged, evt)

	// Keep connection alive with heartbeats; stream GPU metrics every 5s
	ticker := time.NewTicker(5 * time.Second)
	defer ticker.Stop()

	for {
		select {
		case <-ctx.Done():
			return
		case <-ticker.C:
			latestStatus, err := h.fetchStatusFromPython(ctx, correlationID)
			if err != nil {
				latestStatus = contracts.CPUFallbackGPUStatus(h.cfg.GPURequired)
			}
			metricsEvt := contracts.NewBackendEvent(contracts.EventGPUMetricsUpdate, correlationID, nil, nil, latestStatus.Utilization)
			if writeErr := sse.WriteEvent(contracts.EventGPUMetricsUpdate, metricsEvt); writeErr != nil {
				return
			}
		}
	}
}

// ReloadWorkloads handles POST /api/gpu/workloads/reload
func (h *GPUHandler) ReloadWorkloads(w http.ResponseWriter, r *http.Request) {
	correlationID := mw.GetCorrelationID(r)
	ctx := r.Context()

	result, err := h.aiProxy.Post(ctx, "/gpu/workloads/reload", nil, correlationID, mw.GetSessionID(r))
	if err != nil {
		contracts.WriteServiceUnavailable(w, correlationID, "python-ai-service")
		return
	}
	if !result.IsOK() {
		contracts.WriteError(w, correlationID, result.StatusCode, "reload_failed", "GPU workload reload failed", nil)
		return
	}

	status, err := h.fetchStatusFromPython(ctx, correlationID)
	if err != nil {
		status = contracts.CPUFallbackGPUStatus(h.cfg.GPURequired)
	}

	contracts.WriteSuccess(w, correlationID, status.Workloads)
}

// PatchSettings handles PATCH /api/gpu/settings
func (h *GPUHandler) PatchSettings(w http.ResponseWriter, r *http.Request) {
	correlationID := mw.GetCorrelationID(r)
	ctx := r.Context()

	var settings contracts.GPUSettings
	if err := json.NewDecoder(r.Body).Decode(&settings); err != nil {
		contracts.WriteBadRequest(w, correlationID, "invalid_body", "Invalid JSON body")
		return
	}

	result, err := h.aiProxy.Patch(ctx, "/gpu/settings", settings, correlationID, mw.GetSessionID(r))
	if err != nil {
		contracts.WriteServiceUnavailable(w, correlationID, "python-ai-service")
		return
	}
	if !result.IsOK() {
		contracts.WriteError(w, correlationID, result.StatusCode, "settings_update_failed", "GPU settings update failed", nil)
		return
	}

	contracts.WriteSuccess(w, correlationID, settings)
}

func (h *GPUHandler) fetchStatusFromPython(ctx context.Context, correlationID string) (contracts.GPUStatus, error) {
	ctx, cancel := context.WithTimeout(ctx, 5*time.Second)
	defer cancel()

	result, err := h.aiProxy.Get(ctx, "/gpu/status", correlationID, "")
	if err != nil {
		return contracts.GPUStatus{}, err
	}
	if !result.IsOK() {
		return contracts.GPUStatus{}, errServiceError("python-ai-service")
	}

	var envelope struct {
		Ok   bool                  `json:"ok"`
		Data contracts.GPUStatus   `json:"data"`
	}
	if err := json.Unmarshal(result.Body, &envelope); err != nil {
		return contracts.GPUStatus{}, err
	}
	return envelope.Data, nil
}

func (h *GPUHandler) fetchMetricsFromPython(ctx context.Context, correlationID, path string) ([]contracts.GPUMetrics, error) {
	ctx, cancel := context.WithTimeout(ctx, 5*time.Second)
	defer cancel()

	result, err := h.aiProxy.Get(ctx, path, correlationID, "")
	if err != nil {
		return nil, err
	}
	if !result.IsOK() {
		return nil, errServiceError("python-ai-service")
	}

	var envelope struct {
		Ok   bool                    `json:"ok"`
		Data []contracts.GPUMetrics  `json:"data"`
	}
	if err := json.Unmarshal(result.Body, &envelope); err != nil {
		return nil, err
	}
	return envelope.Data, nil
}
