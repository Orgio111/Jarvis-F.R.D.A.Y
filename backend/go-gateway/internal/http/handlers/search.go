package handlers

import (
	"encoding/json"
	"net/http"

	"github.com/orgio111/jarvis/go-gateway/internal/config"
	"github.com/orgio111/jarvis/go-gateway/internal/contracts"
	mw "github.com/orgio111/jarvis/go-gateway/internal/http/middleware"
	"github.com/orgio111/jarvis/go-gateway/internal/proxy"
)

// SearchHandler handles /api/search/* endpoints.
type SearchHandler struct {
	cfg     *config.Config
	aiProxy *proxy.AIProxy
}

func NewSearchHandler(cfg *config.Config, aiProxy *proxy.AIProxy) *SearchHandler {
	return &SearchHandler{cfg: cfg, aiProxy: aiProxy}
}

// Status handles GET /api/search/status
func (h *SearchHandler) Status(w http.ResponseWriter, r *http.Request) {
	correlationID := mw.GetCorrelationID(r)
	sessionID := mw.GetSessionID(r)
	result, err := h.aiProxy.Get(r.Context(), "/search/status", correlationID, sessionID)
	if err != nil || !result.IsOK() {
		contracts.WriteSuccess(w, correlationID, map[string]interface{}{
			"enabled": false, "engine": "duckduckgo",
		})
		return
	}
	var envelope struct{ Data interface{} `json:"data"` }
	_ = result.DecodeInto(&envelope)
	contracts.WriteSuccess(w, correlationID, envelope.Data)
}

// Search handles POST /api/search
func (h *SearchHandler) Search(w http.ResponseWriter, r *http.Request) {
	correlationID := mw.GetCorrelationID(r)
	sessionID := mw.GetSessionID(r)

	var body map[string]interface{}
	if err := json.NewDecoder(r.Body).Decode(&body); err != nil {
		contracts.WriteBadRequest(w, correlationID, "invalid_request", "request body must be valid JSON")
		return
	}

	if _, ok := body["query"]; !ok {
		contracts.WriteBadRequest(w, correlationID, "invalid_request", "query is required")
		return
	}

	result, err := h.aiProxy.Post(r.Context(), "/search", body, correlationID, sessionID)
	if err != nil {
		contracts.WriteServiceUnavailable(w, correlationID, "search service unavailable")
		return
	}
	if !result.IsOK() {
		contracts.WriteError(w, correlationID, result.StatusCode, "search_error", "search failed", nil)
		return
	}
	var envelope struct{ Data interface{} `json:"data"` }
	_ = result.DecodeInto(&envelope)
	contracts.WriteSuccess(w, correlationID, envelope.Data)
}
