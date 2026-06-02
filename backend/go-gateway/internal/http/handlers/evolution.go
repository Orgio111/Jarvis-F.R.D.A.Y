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

// SelfImprovementHandler handles /api/self-improvement/* endpoints.
type SelfImprovementHandler struct {
	cfg     *config.Config
	aiProxy *proxy.AIProxy
}

func NewSelfImprovementHandler(cfg *config.Config, aiProxy *proxy.AIProxy) *SelfImprovementHandler {
	return &SelfImprovementHandler{cfg: cfg, aiProxy: aiProxy}
}

// Status handles GET /api/self-improvement/status
func (h *SelfImprovementHandler) Status(w http.ResponseWriter, r *http.Request) {
	correlationID := mw.GetCorrelationID(r)
	sessionID := mw.GetSessionID(r)
	result, err := h.aiProxy.Get(r.Context(), "/self-improvement/status", correlationID, sessionID)
	if err != nil || !result.IsOK() {
		contracts.WriteSuccess(w, correlationID, map[string]interface{}{
			"enabled": false, "pendingSuggestions": 0, "appliedCount": 0,
		})
		return
	}
	var envelope struct{ Data interface{} `json:"data"` }
	_ = result.DecodeInto(&envelope)
	contracts.WriteSuccess(w, correlationID, envelope.Data)
}

// ListSuggestions handles GET /api/self-improvement/suggestions
func (h *SelfImprovementHandler) ListSuggestions(w http.ResponseWriter, r *http.Request) {
	correlationID := mw.GetCorrelationID(r)
	sessionID := mw.GetSessionID(r)
	result, err := h.aiProxy.Get(r.Context(), "/self-improvement/suggestions", correlationID, sessionID)
	if err != nil || !result.IsOK() {
		contracts.WriteSuccess(w, correlationID, map[string]interface{}{
			"suggestions": []interface{}{}, "total": 0,
		})
		return
	}
	var envelope struct{ Data interface{} `json:"data"` }
	_ = result.DecodeInto(&envelope)
	contracts.WriteSuccess(w, correlationID, envelope.Data)
}

// Suggest handles POST /api/self-improvement/suggest
func (h *SelfImprovementHandler) Suggest(w http.ResponseWriter, r *http.Request) {
	correlationID := mw.GetCorrelationID(r)
	sessionID := mw.GetSessionID(r)

	var body map[string]interface{}
	if err := json.NewDecoder(r.Body).Decode(&body); err != nil {
		contracts.WriteBadRequest(w, correlationID, "invalid_request", "request body must be valid JSON")
		return
	}

	result, err := h.aiProxy.Post(r.Context(), "/self-improvement/suggest", body, correlationID, sessionID)
	if err != nil {
		contracts.WriteServiceUnavailable(w, correlationID, "self-improvement service unavailable")
		return
	}
	if !result.IsOK() {
		contracts.WriteError(w, correlationID, result.StatusCode, "suggestion_error", "failed to create suggestion", nil)
		return
	}
	var envelope struct{ Data interface{} `json:"data"` }
	_ = result.DecodeInto(&envelope)
	contracts.WriteSuccess(w, correlationID, envelope.Data)
}

// Approve handles POST /api/self-improvement/suggestions/{suggestionId}/approve
func (h *SelfImprovementHandler) Approve(w http.ResponseWriter, r *http.Request) {
	correlationID := mw.GetCorrelationID(r)
	sessionID := mw.GetSessionID(r)
	suggestionID := chi.URLParam(r, "suggestionId")

	result, err := h.aiProxy.Post(r.Context(), "/self-improvement/suggestions/"+suggestionID+"/approve", nil, correlationID, sessionID)
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

// Reject handles POST /api/self-improvement/suggestions/{suggestionId}/reject
func (h *SelfImprovementHandler) Reject(w http.ResponseWriter, r *http.Request) {
	correlationID := mw.GetCorrelationID(r)
	sessionID := mw.GetSessionID(r)
	suggestionID := chi.URLParam(r, "suggestionId")

	result, err := h.aiProxy.Post(r.Context(), "/self-improvement/suggestions/"+suggestionID+"/reject", nil, correlationID, sessionID)
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
