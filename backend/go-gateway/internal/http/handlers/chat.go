package handlers

import (
	"bufio"
	"context"
	"encoding/json"
	"errors"
	"io"
	"net/http"
	"time"

	"github.com/orgio111/jarvis/go-gateway/internal/config"
	"github.com/orgio111/jarvis/go-gateway/internal/contracts"
	mw "github.com/orgio111/jarvis/go-gateway/internal/http/middleware"
	"github.com/orgio111/jarvis/go-gateway/internal/proxy"
)

// ChatHandler handles /api/chat/* endpoints.
type ChatHandler struct {
	cfg     *config.Config
	aiProxy *proxy.AIProxy
}

// NewChatHandler creates a ChatHandler.
func NewChatHandler(cfg *config.Config, aiProxy *proxy.AIProxy) *ChatHandler {
	return &ChatHandler{cfg: cfg, aiProxy: aiProxy}
}

// Completions handles POST /api/chat/completions
func (h *ChatHandler) Completions(w http.ResponseWriter, r *http.Request) {
	correlationID := mw.GetCorrelationID(r)
	sessionID := mw.GetSessionID(r)

	var body map[string]interface{}
	if err := json.NewDecoder(r.Body).Decode(&body); err != nil {
		contracts.WriteBadRequest(w, correlationID, "invalid_request", "request body must be valid JSON")
		return
	}

	// Default stream=true
	streamEnabled := true
	if v, ok := body["stream"]; ok {
		if b, ok := v.(bool); ok {
			streamEnabled = b
		}
	}

	if streamEnabled {
		h.streamCompletions(w, r, body, correlationID, sessionID)
		return
	}

	result, err := h.aiProxy.Post(r.Context(), "/chat/completions", body, correlationID, sessionID)
	if err != nil {
		contracts.WriteServiceUnavailable(w, correlationID, "AI service unavailable")
		return
	}
	if !result.IsOK() {
		contracts.WriteError(w, correlationID, result.StatusCode, "chat_error", "chat completion failed", nil)
		return
	}
	var data interface{}
	_ = result.DecodeInto(&data)
	contracts.WriteSuccess(w, correlationID, data)
}

// streamCompletions pipes the Python SSE stream through AIProxy (circuit breaker aware).
func (h *ChatHandler) streamCompletions(
	w http.ResponseWriter,
	r *http.Request,
	body map[string]interface{},
	correlationID, sessionID string,
) {
	flusher, ok := w.(http.Flusher)
	if !ok {
		contracts.WriteServiceUnavailable(w, correlationID, "streaming not supported by this response writer")
		return
	}

	body["stream"] = true

	ctx, cancel := context.WithTimeout(r.Context(), 5*time.Minute)
	defer cancel()

	stream, err := h.aiProxy.Stream(ctx, "/chat/completions", body, correlationID, sessionID)
	if err != nil {
		if errors.Is(err, proxy.ErrCircuitOpen) {
			contracts.WriteCircuitOpen(w, correlationID, "ai-service")
			return
		}
		contracts.WriteServiceUnavailable(w, correlationID, "python-ai-service request failed")
		return
	}
	defer stream.Body.Close()

	// Set SSE headers and start streaming.
	w.Header().Set("Content-Type", "text/event-stream")
	w.Header().Set("Cache-Control", "no-cache")
	w.Header().Set("Connection", "keep-alive")
	w.Header().Set("X-Accel-Buffering", "no")
	w.WriteHeader(http.StatusOK)
	flusher.Flush()

	scanner := bufio.NewScanner(stream.Body)
	for scanner.Scan() {
		line := scanner.Text()
		if line == "" {
			continue
		}
		if _, writeErr := io.WriteString(w, line+"\n\n"); writeErr != nil {
			return
		}
		flusher.Flush()
		if line == "data: [DONE]" {
			return
		}
	}
}

// History handles GET /api/chat/history (stub — future implementation)
func (h *ChatHandler) History(w http.ResponseWriter, r *http.Request) {
	correlationID := mw.GetCorrelationID(r)
	contracts.WriteSuccess(w, correlationID, map[string]interface{}{
		"messages": []interface{}{},
		"total":    0,
	})
}
