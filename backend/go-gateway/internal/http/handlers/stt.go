package handlers

import (
	"bytes"
	"encoding/json"
	"io"
	"net/http"

	"github.com/orgio111/jarvis/go-gateway/internal/config"
	"github.com/orgio111/jarvis/go-gateway/internal/contracts"
	mw "github.com/orgio111/jarvis/go-gateway/internal/http/middleware"
	"github.com/orgio111/jarvis/go-gateway/internal/proxy"
)

// STTHandler handles /api/stt/* endpoints.
type STTHandler struct {
	cfg     *config.Config
	aiProxy *proxy.AIProxy
}

// NewSTTHandler creates an STTHandler.
func NewSTTHandler(cfg *config.Config, aiProxy *proxy.AIProxy) *STTHandler {
	return &STTHandler{cfg: cfg, aiProxy: aiProxy}
}

// Status handles GET /api/stt/status
func (h *STTHandler) Status(w http.ResponseWriter, r *http.Request) {
	correlationID := mw.GetCorrelationID(r)
	sessionID := mw.GetSessionID(r)

	result, err := h.aiProxy.Get(r.Context(), "/stt/status", correlationID, sessionID)
	if err != nil {
		contracts.WriteServiceUnavailable(w, correlationID, "python-ai-service")
		return
	}

	var raw any
	_ = json.Unmarshal(result.Body, &raw)
	contracts.WriteRaw(w, result.StatusCode, raw)
}

// Transcribe handles POST /api/stt/transcribe — forwards multipart audio to Python
func (h *STTHandler) Transcribe(w http.ResponseWriter, r *http.Request) {
	correlationID := mw.GetCorrelationID(r)
	sessionID := mw.GetSessionID(r)

	body, err := io.ReadAll(r.Body)
	if err != nil {
		contracts.WriteInternalError(w, correlationID)
		return
	}

	// Forward the raw multipart body to the Python service, preserving
	// Content-Type so the multipart boundary is not lost.
	req, err := http.NewRequestWithContext(r.Context(), http.MethodPost,
		h.cfg.PythonAIServiceURL+"/stt/transcribe", bytes.NewReader(body))
	if err != nil {
		contracts.WriteInternalError(w, correlationID)
		return
	}
	req.Header.Set("Content-Type", r.Header.Get("Content-Type"))
	req.Header.Set("X-Correlation-ID", correlationID)
	req.Header.Set("X-Session-ID", sessionID)
	req.Header.Set("X-Source", "go-gateway")

	resp, err := http.DefaultClient.Do(req)
	if err != nil {
		contracts.WriteServiceUnavailable(w, correlationID, "STT service unavailable")
		return
	}
	defer resp.Body.Close()

	var data any
	if err := json.NewDecoder(resp.Body).Decode(&data); err != nil {
		contracts.WriteInternalError(w, correlationID)
		return
	}
	contracts.WriteSuccess(w, correlationID, data)
}
