package handlers

import (
	"bufio"
	"fmt"
	"net/http"
	"strings"
	"sync"
	"time"

	"github.com/go-chi/chi/v5"
	"github.com/gorilla/websocket"

	"github.com/orgio111/jarvis/go-gateway/internal/config"
)

var wsUpgrader = websocket.Upgrader{
	ReadBufferSize:  1024,
	WriteBufferSize: 4096,
	// Allow all origins — gateway's CORS middleware handles origin policy.
	CheckOrigin: func(r *http.Request) bool { return true },
}

// EventsHandler proxies Rust broker SSE streams to WebSocket clients.
type EventsHandler struct {
	brokerURL  string
	httpClient *http.Client
}

func NewEventsHandler(cfg *config.Config) *EventsHandler {
	return &EventsHandler{
		brokerURL:  strings.TrimRight(cfg.RustBrokerURL, "/"),
		httpClient: &http.Client{}, // no global timeout — SSE streams are long-lived
	}
}

// Stream upgrades the HTTP connection to WebSocket and proxies the Rust broker's
// SSE stream for the given :topic, forwarding each "data:" line as a WS text frame.
func (h *EventsHandler) Stream(w http.ResponseWriter, r *http.Request) {
	topic := chi.URLParam(r, "topic")
	if topic == "" {
		http.Error(w, "missing topic", http.StatusBadRequest)
		return
	}

	conn, err := wsUpgrader.Upgrade(w, r, nil)
	if err != nil {
		return
	}
	defer conn.Close()

	sseURL := fmt.Sprintf("%s/events/stream/%s", h.brokerURL, topic)
	req, err := http.NewRequestWithContext(r.Context(), http.MethodGet, sseURL, nil)
	if err != nil {
		_ = conn.WriteMessage(
			websocket.CloseMessage,
			websocket.FormatCloseMessage(websocket.CloseInternalServerErr, "broker connect error"),
		)
		return
	}
	req.Header.Set("Accept", "text/event-stream")
	req.Header.Set("Cache-Control", "no-cache")

	resp, err := h.httpClient.Do(req)
	if err != nil {
		_ = conn.WriteMessage(
			websocket.CloseMessage,
			websocket.FormatCloseMessage(websocket.CloseInternalServerErr, "broker unavailable"),
		)
		return
	}

	// closeBody ensures resp.Body.Close is called exactly once regardless of
	// which goroutine (disconnect reader vs. SSE scanner) triggers the shutdown.
	var closeOnce sync.Once
	closeBody := func() { closeOnce.Do(func() { resp.Body.Close() }) }
	defer closeBody()

	// Drain client pings / detect disconnect so we can interrupt the SSE read.
	go func() {
		conn.SetReadDeadline(time.Time{})
		for {
			if _, _, err := conn.ReadMessage(); err != nil {
				closeBody()
				return
			}
		}
	}()

	scanner := bufio.NewScanner(resp.Body)
	for scanner.Scan() {
		line := scanner.Text()
		if strings.HasPrefix(line, "data: ") {
			payload := strings.TrimPrefix(line, "data: ")
			if err := conn.WriteMessage(websocket.TextMessage, []byte(payload)); err != nil {
				return
			}
		}
	}
}
