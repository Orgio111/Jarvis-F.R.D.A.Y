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

// LocalActionsHandler handles /api/local-actions/* endpoints.
type LocalActionsHandler struct {
	cfg     *config.Config
	aiProxy *proxy.AIProxy
}

func NewLocalActionsHandler(cfg *config.Config, aiProxy *proxy.AIProxy) *LocalActionsHandler {
	return &LocalActionsHandler{cfg: cfg, aiProxy: aiProxy}
}

// List handles GET /api/local-actions
func (h *LocalActionsHandler) List(w http.ResponseWriter, r *http.Request) {
	correlationID := mw.GetCorrelationID(r)
	sessionID := mw.GetSessionID(r)
	result, err := h.aiProxy.Get(r.Context(), "/local-actions", correlationID, sessionID)
	if err != nil || !result.IsOK() {
		contracts.WriteSuccess(w, correlationID, map[string]interface{}{
			"actions": []interface{}{}, "total": 0, "enabled": false,
		})
		return
	}
	var envelope struct{ Data interface{} `json:"data"` }
	_ = result.DecodeInto(&envelope)
	contracts.WriteSuccess(w, correlationID, envelope.Data)
}

// ListPending handles GET /api/local-actions/pending
func (h *LocalActionsHandler) ListPending(w http.ResponseWriter, r *http.Request) {
	correlationID := mw.GetCorrelationID(r)
	sessionID := mw.GetSessionID(r)
	result, err := h.aiProxy.Get(r.Context(), "/local-actions/pending", correlationID, sessionID)
	if err != nil || !result.IsOK() {
		contracts.WriteSuccess(w, correlationID, map[string]interface{}{
			"pending": []interface{}{}, "total": 0,
		})
		return
	}
	var envelope struct{ Data interface{} `json:"data"` }
	_ = result.DecodeInto(&envelope)
	contracts.WriteSuccess(w, correlationID, envelope.Data)
}

// Execute handles POST /api/local-actions/{actionId}/execute
func (h *LocalActionsHandler) Execute(w http.ResponseWriter, r *http.Request) {
	correlationID := mw.GetCorrelationID(r)
	sessionID := mw.GetSessionID(r)
	actionID := chi.URLParam(r, "actionId")

	var body map[string]interface{}
	_ = json.NewDecoder(r.Body).Decode(&body)

	result, err := h.aiProxy.Post(r.Context(), "/local-actions/"+actionID+"/execute", body, correlationID, sessionID)
	if err != nil {
		contracts.WriteServiceUnavailable(w, correlationID, "local actions service unavailable")
		return
	}
	if result.StatusCode == http.StatusNotFound {
		contracts.WriteNotFound(w, correlationID)
		return
	}
	if result.StatusCode == http.StatusServiceUnavailable {
		contracts.WriteServiceUnavailable(w, correlationID, "local PC control is disabled")
		return
	}
	var envelope struct{ Data interface{} `json:"data"` }
	_ = result.DecodeInto(&envelope)
	contracts.WriteSuccess(w, correlationID, envelope.Data)
}

// Approve handles POST /api/local-actions/approvals/{approvalId}/approve
func (h *LocalActionsHandler) Approve(w http.ResponseWriter, r *http.Request) {
	correlationID := mw.GetCorrelationID(r)
	sessionID := mw.GetSessionID(r)
	approvalID := chi.URLParam(r, "approvalId")

	result, err := h.aiProxy.Post(r.Context(), "/local-actions/approvals/"+approvalID+"/approve", nil, correlationID, sessionID)
	if err != nil {
		contracts.WriteInternalError(w, correlationID)
		return
	}
	if result.StatusCode == http.StatusNotFound {
		contracts.WriteNotFound(w, correlationID)
		return
	}
	var envelope struct{ Data interface{} `json:"data"` }
	_ = result.DecodeInto(&envelope)
	contracts.WriteSuccess(w, correlationID, envelope.Data)
}

// Deny handles POST /api/local-actions/approvals/{approvalId}/deny
func (h *LocalActionsHandler) Deny(w http.ResponseWriter, r *http.Request) {
	correlationID := mw.GetCorrelationID(r)
	sessionID := mw.GetSessionID(r)
	approvalID := chi.URLParam(r, "approvalId")

	result, err := h.aiProxy.Post(r.Context(), "/local-actions/approvals/"+approvalID+"/deny", nil, correlationID, sessionID)
	if err != nil {
		contracts.WriteInternalError(w, correlationID)
		return
	}
	if result.StatusCode == http.StatusNotFound {
		contracts.WriteNotFound(w, correlationID)
		return
	}
	var envelope struct{ Data interface{} `json:"data"` }
	_ = result.DecodeInto(&envelope)
	contracts.WriteSuccess(w, correlationID, envelope.Data)
}
