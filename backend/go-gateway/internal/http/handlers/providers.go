package handlers

import (
	"net/http"

	"github.com/go-chi/chi/v5"

	"github.com/orgio111/jarvis/go-gateway/internal/config"
	"github.com/orgio111/jarvis/go-gateway/internal/contracts"
	mw "github.com/orgio111/jarvis/go-gateway/internal/http/middleware"
	"github.com/orgio111/jarvis/go-gateway/internal/proxy"
)

// ProvidersHandler handles /api/providers/* endpoints.
type ProvidersHandler struct {
	cfg     *config.Config
	aiProxy *proxy.AIProxy
}

// NewProvidersHandler creates a ProvidersHandler.
func NewProvidersHandler(cfg *config.Config, aiProxy *proxy.AIProxy) *ProvidersHandler {
	return &ProvidersHandler{cfg: cfg, aiProxy: aiProxy}
}

// List handles GET /api/providers
func (h *ProvidersHandler) List(w http.ResponseWriter, r *http.Request) {
	correlationID := mw.GetCorrelationID(r)
	sessionID := mw.GetSessionID(r)
	result, err := h.aiProxy.Get(r.Context(), "/providers", correlationID, sessionID)
	if err != nil || !result.IsOK() {
		contracts.WriteSuccess(w, correlationID, []interface{}{})
		return
	}
	var envelope struct {
		Data interface{} `json:"data"`
	}
	if err := result.DecodeInto(&envelope); err != nil {
		contracts.WriteSuccess(w, correlationID, []interface{}{})
		return
	}
	contracts.WriteSuccess(w, correlationID, envelope.Data)
}

// Get handles GET /api/providers/{providerId}
func (h *ProvidersHandler) Get(w http.ResponseWriter, r *http.Request) {
	correlationID := mw.GetCorrelationID(r)
	sessionID := mw.GetSessionID(r)
	providerID := chi.URLParam(r, "providerId")
	result, err := h.aiProxy.Get(r.Context(), "/providers/"+providerID, correlationID, sessionID)
	if err != nil {
		contracts.WriteServiceUnavailable(w, correlationID, "provider service unavailable")
		return
	}
	if result.StatusCode == http.StatusNotFound {
		contracts.WriteNotFound(w, correlationID)
		return
	}
	if !result.IsOK() {
		contracts.WriteServiceUnavailable(w, correlationID, "provider service unavailable")
		return
	}
	var envelope struct {
		Data interface{} `json:"data"`
	}
	if err := result.DecodeInto(&envelope); err != nil {
		contracts.WriteInternalError(w, correlationID)
		return
	}
	contracts.WriteSuccess(w, correlationID, envelope.Data)
}
