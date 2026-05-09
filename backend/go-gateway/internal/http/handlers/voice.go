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

// VoiceHandler handles /api/voice/* endpoints.
type VoiceHandler struct {
	cfg     *config.Config
	aiProxy *proxy.AIProxy
}

func NewVoiceHandler(cfg *config.Config, aiProxy *proxy.AIProxy) *VoiceHandler {
	return &VoiceHandler{cfg: cfg, aiProxy: aiProxy}
}

// Status handles GET /api/voice/status
func (h *VoiceHandler) Status(w http.ResponseWriter, r *http.Request) {
	correlationID := mw.GetCorrelationID(r)
	sessionID := mw.GetSessionID(r)
	result, err := h.aiProxy.Get(r.Context(), "/voice/status", correlationID, sessionID)
	if err != nil || !result.IsOK() {
		contracts.WriteSuccess(w, correlationID, map[string]interface{}{
			"stt": map[string]interface{}{"enabled": false, "available": false},
			"tts": map[string]interface{}{"enabled": false, "available": false},
		})
		return
	}
	var envelope struct {
		Data interface{} `json:"data"`
	}
	_ = result.DecodeInto(&envelope)
	contracts.WriteSuccess(w, correlationID, envelope.Data)
}

// STT handles POST /api/voice/stt — forwards multipart audio to Python
func (h *VoiceHandler) STT(w http.ResponseWriter, r *http.Request) {
	correlationID := mw.GetCorrelationID(r)
	sessionID := mw.GetSessionID(r)

	body, err := io.ReadAll(r.Body)
	if err != nil {
		contracts.WriteInternalError(w, correlationID)
		return
	}

	req, err := http.NewRequestWithContext(r.Context(), http.MethodPost,
		h.cfg.PythonAIServiceURL+"/voice/stt", bytes.NewReader(body))
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
		contracts.WriteServiceUnavailable(w, correlationID, "voice STT service unavailable")
		return
	}
	defer resp.Body.Close()

	var data interface{}
	if err := json.NewDecoder(resp.Body).Decode(&data); err != nil {
		contracts.WriteInternalError(w, correlationID)
		return
	}
	contracts.WriteSuccess(w, correlationID, data)
}

// TTS handles POST /api/voice/tts
func (h *VoiceHandler) TTS(w http.ResponseWriter, r *http.Request) {
	correlationID := mw.GetCorrelationID(r)
	sessionID := mw.GetSessionID(r)

	var body map[string]interface{}
	if err := json.NewDecoder(r.Body).Decode(&body); err != nil {
		contracts.WriteBadRequest(w, correlationID, "invalid_request", "request body must be valid JSON")
		return
	}

	result, err := h.aiProxy.Post(r.Context(), "/voice/tts", body, correlationID, sessionID)
	if err != nil {
		contracts.WriteServiceUnavailable(w, correlationID, "TTS service unavailable")
		return
	}
	if result.StatusCode == http.StatusNoContent {
		w.WriteHeader(http.StatusNoContent)
		return
	}
	var data interface{}
	_ = json.Unmarshal(result.Body, &data)
	contracts.WriteSuccess(w, correlationID, data)
}
