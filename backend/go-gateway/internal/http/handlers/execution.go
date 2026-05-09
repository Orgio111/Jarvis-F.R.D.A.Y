package handlers

import (
	"encoding/json"
	"net/http"

	"github.com/orgio111/jarvis/go-gateway/internal/config"
	"github.com/orgio111/jarvis/go-gateway/internal/contracts"
	mw "github.com/orgio111/jarvis/go-gateway/internal/http/middleware"
	"github.com/orgio111/jarvis/go-gateway/internal/proxy"
)

// ExecutionHandler handles /api/execution/* endpoints.
type ExecutionHandler struct {
	cfg     *config.Config
	aiProxy *proxy.AIProxy
}

func NewExecutionHandler(cfg *config.Config, aiProxy *proxy.AIProxy) *ExecutionHandler {
	return &ExecutionHandler{cfg: cfg, aiProxy: aiProxy}
}

// Status handles GET /api/execution/status
func (h *ExecutionHandler) Status(w http.ResponseWriter, r *http.Request) {
	correlationID := mw.GetCorrelationID(r)
	sessionID := mw.GetSessionID(r)
	result, err := h.aiProxy.Get(r.Context(), "/execution/status", correlationID, sessionID)
	if err != nil || !result.IsOK() {
		contracts.WriteSuccess(w, correlationID, map[string]interface{}{
			"enabled": false, "languages": []string{},
		})
		return
	}
	var envelope struct{ Data interface{} `json:"data"` }
	_ = result.DecodeInto(&envelope)
	contracts.WriteSuccess(w, correlationID, envelope.Data)
}

// Run handles POST /api/execution/run
func (h *ExecutionHandler) Run(w http.ResponseWriter, r *http.Request) {
	correlationID := mw.GetCorrelationID(r)
	sessionID := mw.GetSessionID(r)
	var body map[string]interface{}
	if err := json.NewDecoder(r.Body).Decode(&body); err != nil {
		contracts.WriteBadRequest(w, correlationID, "invalid_request", "request body must be valid JSON")
		return
	}
	result, err := h.aiProxy.Post(r.Context(), "/execution/run", body, correlationID, sessionID)
	if err != nil {
		contracts.WriteServiceUnavailable(w, correlationID, "execution service unavailable")
		return
	}
	if !result.IsOK() {
		var errEnv interface{}
		_ = json.Unmarshal(result.Body, &errEnv)
		contracts.WriteError(w, correlationID, result.StatusCode, "execution_error", "execution failed", nil)
		return
	}
	var envelope struct{ Data interface{} `json:"data"` }
	_ = result.DecodeInto(&envelope)
	contracts.WriteSuccess(w, correlationID, envelope.Data)
}
