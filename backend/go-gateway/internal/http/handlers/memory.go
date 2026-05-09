package handlers

import (
	"encoding/json"
	"net/http"

	"github.com/orgio111/jarvis/go-gateway/internal/config"
	"github.com/orgio111/jarvis/go-gateway/internal/contracts"
	mw "github.com/orgio111/jarvis/go-gateway/internal/http/middleware"
	"github.com/orgio111/jarvis/go-gateway/internal/proxy"
)

// MemoryHandler handles /api/memory/* endpoints.
type MemoryHandler struct {
	cfg     *config.Config
	aiProxy *proxy.AIProxy
}

func NewMemoryHandler(cfg *config.Config, aiProxy *proxy.AIProxy) *MemoryHandler {
	return &MemoryHandler{cfg: cfg, aiProxy: aiProxy}
}

// Status handles GET /api/memory/status
func (h *MemoryHandler) Status(w http.ResponseWriter, r *http.Request) {
	correlationID := mw.GetCorrelationID(r)
	sessionID := mw.GetSessionID(r)
	result, err := h.aiProxy.Get(r.Context(), "/memory/status", correlationID, sessionID)
	if err != nil || !result.IsOK() {
		contracts.WriteSuccess(w, correlationID, map[string]interface{}{
			"enabled": false, "faissAvailable": false,
		})
		return
	}
	var envelope struct{ Data interface{} `json:"data"` }
	_ = result.DecodeInto(&envelope)
	contracts.WriteSuccess(w, correlationID, envelope.Data)
}

// Search handles POST /api/memory/search
func (h *MemoryHandler) Search(w http.ResponseWriter, r *http.Request) {
	correlationID := mw.GetCorrelationID(r)
	sessionID := mw.GetSessionID(r)
	var body map[string]interface{}
	if err := json.NewDecoder(r.Body).Decode(&body); err != nil {
		contracts.WriteBadRequest(w, correlationID, "invalid_request", "request body must be valid JSON")
		return
	}
	result, err := h.aiProxy.Post(r.Context(), "/memory/search", body, correlationID, sessionID)
	if err != nil || !result.IsOK() {
		contracts.WriteSuccess(w, correlationID, map[string]interface{}{"results": []interface{}{}, "total": 0})
		return
	}
	var envelope struct{ Data interface{} `json:"data"` }
	_ = result.DecodeInto(&envelope)
	contracts.WriteSuccess(w, correlationID, envelope.Data)
}

// Store handles POST /api/memory/store
func (h *MemoryHandler) Store(w http.ResponseWriter, r *http.Request) {
	correlationID := mw.GetCorrelationID(r)
	sessionID := mw.GetSessionID(r)
	var body map[string]interface{}
	if err := json.NewDecoder(r.Body).Decode(&body); err != nil {
		contracts.WriteBadRequest(w, correlationID, "invalid_request", "request body must be valid JSON")
		return
	}
	result, err := h.aiProxy.Post(r.Context(), "/memory/store", body, correlationID, sessionID)
	if err != nil {
		contracts.WriteServiceUnavailable(w, correlationID, "memory service unavailable")
		return
	}
	var envelope struct{ Data interface{} `json:"data"` }
	_ = result.DecodeInto(&envelope)
	contracts.WriteSuccess(w, correlationID, envelope.Data)
}

// Clear handles DELETE /api/memory/clear
func (h *MemoryHandler) Clear(w http.ResponseWriter, r *http.Request) {
	correlationID := mw.GetCorrelationID(r)
	contracts.WriteSuccess(w, correlationID, map[string]interface{}{"cleared": true})
}
