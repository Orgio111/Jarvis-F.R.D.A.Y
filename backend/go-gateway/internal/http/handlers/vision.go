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

// VisionHandler handles /api/vision/* endpoints.
type VisionHandler struct {
	cfg     *config.Config
	aiProxy *proxy.AIProxy
}

func NewVisionHandler(cfg *config.Config, aiProxy *proxy.AIProxy) *VisionHandler {
	return &VisionHandler{cfg: cfg, aiProxy: aiProxy}
}

// Status handles GET /api/vision/status
func (h *VisionHandler) Status(w http.ResponseWriter, r *http.Request) {
	correlationID := mw.GetCorrelationID(r)
	sessionID := mw.GetSessionID(r)
	result, err := h.aiProxy.Get(r.Context(), "/vision/status", correlationID, sessionID)
	if err != nil || !result.IsOK() {
		contracts.WriteSuccess(w, correlationID, map[string]interface{}{
			"enabled": false, "providerSupportsVision": false, "maxImageSizeMb": 20,
		})
		return
	}
	var envelope struct{ Data interface{} `json:"data"` }
	_ = result.DecodeInto(&envelope)
	contracts.WriteSuccess(w, correlationID, envelope.Data)
}

// Analyze handles POST /api/vision/analyze — forwards multipart image to Python
func (h *VisionHandler) Analyze(w http.ResponseWriter, r *http.Request) {
	correlationID := mw.GetCorrelationID(r)
	sessionID := mw.GetSessionID(r)

	body, err := io.ReadAll(r.Body)
	if err != nil {
		contracts.WriteInternalError(w, correlationID)
		return
	}

	req, err := http.NewRequestWithContext(r.Context(), http.MethodPost,
		h.cfg.PythonAIServiceURL+"/vision/analyze", bytes.NewReader(body))
	if err != nil {
		contracts.WriteInternalError(w, correlationID)
		return
	}
	req.Header.Set("Content-Type", r.Header.Get("Content-Type"))
	req.Header.Set("X-Correlation-ID", correlationID)
	req.Header.Set("X-Session-ID", sessionID)
	req.Header.Set("X-Source", "go-gateway")
	if prompt := r.Header.Get("X-Vision-Prompt"); prompt != "" {
		req.Header.Set("X-Vision-Prompt", prompt)
	}

	resp, err := http.DefaultClient.Do(req)
	if err != nil {
		contracts.WriteServiceUnavailable(w, correlationID, "vision service unavailable")
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
