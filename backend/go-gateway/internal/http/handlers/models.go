package handlers

import (
	"net/http"

	"github.com/orgio111/jarvis/go-gateway/internal/config"
	"github.com/orgio111/jarvis/go-gateway/internal/contracts"
	mw "github.com/orgio111/jarvis/go-gateway/internal/http/middleware"
	"github.com/orgio111/jarvis/go-gateway/internal/proxy"
)

// ModelsHandler handles /api/models/* endpoints.
type ModelsHandler struct {
	cfg     *config.Config
	aiProxy *proxy.AIProxy
}

// NewModelsHandler creates a ModelsHandler.
func NewModelsHandler(cfg *config.Config, aiProxy *proxy.AIProxy) *ModelsHandler {
	return &ModelsHandler{cfg: cfg, aiProxy: aiProxy}
}

// List handles GET /api/models
func (h *ModelsHandler) List(w http.ResponseWriter, r *http.Request) {
	correlationID := mw.GetCorrelationID(r)
	sessionID := mw.GetSessionID(r)
	path := "/models"
	if p := r.URL.Query().Get("provider"); p != "" {
		path += "?provider=" + p
	}
	result, err := h.aiProxy.Get(r.Context(), path, correlationID, sessionID)
	if err != nil || !result.IsOK() {
		contracts.WriteSuccess(w, correlationID, map[string]interface{}{
			"models": []interface{}{},
			"total":  0,
		})
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
