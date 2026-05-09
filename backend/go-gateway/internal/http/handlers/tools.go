package handlers

import (
	"encoding/json"
	"net/http"

	"github.com/go-chi/chi/v5"

	"github.com/orgio111/jarvis/go-gateway/internal/config"
	"github.com/orgio111/jarvis/go-gateway/internal/contracts"
	mw "github.com/orgio111/jarvis/go-gateway/internal/http/middleware"
	"github.com/orgio111/jarvis/go-gateway/internal/proxy"
)

// ToolsHandler handles /api/tools/* endpoints.
type ToolsHandler struct {
	cfg     *config.Config
	aiProxy *proxy.AIProxy
}

func NewToolsHandler(cfg *config.Config, aiProxy *proxy.AIProxy) *ToolsHandler {
	return &ToolsHandler{cfg: cfg, aiProxy: aiProxy}
}

// List handles GET /api/tools
func (h *ToolsHandler) List(w http.ResponseWriter, r *http.Request) {
	correlationID := mw.GetCorrelationID(r)
	sessionID := mw.GetSessionID(r)
	result, err := h.aiProxy.Get(r.Context(), "/tools", correlationID, sessionID)
	if err != nil || !result.IsOK() {
		contracts.WriteSuccess(w, correlationID, map[string]interface{}{
			"tools": []interface{}{}, "total": 0, "enabled": 0,
		})
		return
	}
	var envelope struct{ Data interface{} `json:"data"` }
	_ = result.DecodeInto(&envelope)
	contracts.WriteSuccess(w, correlationID, envelope.Data)
}

// Execute handles POST /api/tools/{toolId}/execute
func (h *ToolsHandler) Execute(w http.ResponseWriter, r *http.Request) {
	correlationID := mw.GetCorrelationID(r)
	sessionID := mw.GetSessionID(r)
	toolID := chi.URLParam(r, "toolId")

	var body map[string]interface{}
	if err := json.NewDecoder(r.Body).Decode(&body); err != nil {
		contracts.WriteBadRequest(w, correlationID, "invalid_request", "request body must be valid JSON")
		return
	}

	result, err := h.aiProxy.Post(r.Context(), "/tools/"+toolID+"/execute", body, correlationID, sessionID)
	if err != nil {
		contracts.WriteServiceUnavailable(w, correlationID, "tools service unavailable")
		return
	}
	if result.StatusCode == http.StatusNotFound {
		contracts.WriteNotFound(w, correlationID)
		return
	}
	if !result.IsOK() {
		contracts.WriteError(w, correlationID, result.StatusCode, "tool_error", "tool execution failed", nil)
		return
	}
	var envelope struct{ Data interface{} `json:"data"` }
	_ = result.DecodeInto(&envelope)
	contracts.WriteSuccess(w, correlationID, envelope.Data)
}
