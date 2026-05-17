package handlers

import (
	"bufio"
	"bytes"
	"context"
	"encoding/json"
	"io"
	"net/http"
	"net/url"
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

// streamCompletions pipes the Python SSE stream directly to the HTTP response.
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

	pythonURL := h.cfg.PythonAIServiceURL
	if pythonURL == "" {
		contracts.WriteServiceUnavailable(w, correlationID, "python-ai-service is not configured (empty PythonAIServiceURL)")
		return
	}

	// Basic validation: require scheme/host so we don't create invalid outbound requests.
	parsed, parseErr := url.Parse(pythonURL)
	if parseErr != nil || parsed == nil || parsed.Scheme == "" || parsed.Host == "" {
		contracts.WriteServiceUnavailable(w, correlationID,
			"python-ai-service is not configured (invalid PythonAIServiceURL: "+pythonURL+")")
		return
	}

	body["stream"] = true
	payload, err := json.Marshal(body)
	if err != nil {
		contracts.WriteServiceUnavailable(w, correlationID, "failed to serialize chat request payload")
		return
	}

	ctx, cancel := context.WithTimeout(r.Context(), 5*time.Minute)
	defer cancel()

	outboundURL := pythonURL + "/chat/completions"
	req, err := http.NewRequestWithContext(ctx, http.MethodPost,
		outboundURL,
		bytes.NewReader(payload),
	)
	if err != nil {
		contracts.WriteServiceUnavailable(w, correlationID, "failed to create request to python-ai-service")
		return
	}
	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("X-Correlation-ID", correlationID)
	req.Header.Set("X-Session-ID", sessionID)
	req.Header.Set("X-Source", "go-gateway")
	req.Header.Set("Accept", "text/event-stream")

	streamClient := &http.Client{Timeout: 0}
	resp, err := streamClient.Do(req)
	if err != nil {
		contracts.WriteServiceUnavailable(w, correlationID, "python-ai-service request failed")
		return
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		raw, _ := io.ReadAll(resp.Body)
		var errEnv interface{}
		_ = json.Unmarshal(raw, &errEnv)
		contracts.WriteError(w, correlationID, resp.StatusCode, "chat_error", "chat service error", nil)
		return
	}

	// Set SSE headers and start streaming
	w.Header().Set("Content-Type", "text/event-stream")
	w.Header().Set("Cache-Control", "no-cache")
	w.Header().Set("Connection", "keep-alive")
	w.Header().Set("X-Accel-Buffering", "no")
	w.WriteHeader(http.StatusOK)
	flusher.Flush()

	scanner := bufio.NewScanner(resp.Body)
	for scanner.Scan() {
		line := scanner.Text()
		if line == "" {
			continue
		}
		if _, err := io.WriteString(w, line+"\n\n"); err != nil {
			contracts.WriteServiceUnavailable(w, correlationID, "failed to stream response to client")
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
