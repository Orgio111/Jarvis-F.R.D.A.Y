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

// Connection-level tuning. These are conservative defaults that:
//   - hard-cap how long a write can stall on a slow client (writeDeadline)
//   - prevent silent dead-NAT connections (ping/pong)
//   - keep the per-connection memory footprint bounded (outboundQueue)
//   - allow events larger than 64KB (scannerMaxBuf)
const (
	writeDeadline  = 10 * time.Second
	pongTimeout    = 60 * time.Second
	pingInterval   = (pongTimeout * 9) / 10 // ping at 90% of pong wait
	outboundQueue  = 256                    // frames; slow client gets disconnected past this
	scannerInitBuf = 64 * 1024
	scannerMaxBuf  = 1024 * 1024 // 1 MB — events larger than this are dropped
)

var wsUpgrader = websocket.Upgrader{
	ReadBufferSize:  1024,
	WriteBufferSize: 4096,
	// Allow all origins — gateway's CORS middleware handles origin policy.
	CheckOrigin: func(r *http.Request) bool { return true },
	// Enable permessage-deflate negotiation. Cheap on small JSON, big win
	// on chat completion streams where each frame is highly compressible.
	EnableCompression: true,
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
//
// Architecture: 3 goroutines per connection.
//
//	  reader     — drains client frames (pings, disconnect detection)
//	  writer     — consumes outbound chan, applies write deadlines, sends pings
//	  pump (main) — reads SSE lines, enqueues onto outbound chan (non-blocking)
//
// If the outbound channel fills (slow client) the connection is dropped rather
// than letting the broker pipeline back up.
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

	// Per-message-deflate at fastest compression — text JSON shrinks ~3-5x
	// and at level 1 the CPU cost is negligible.
	conn.EnableWriteCompression(true)
	_ = conn.SetCompressionLevel(1)

	// Initial read deadline; pong handler refreshes it on every pong.
	_ = conn.SetReadDeadline(time.Now().Add(pongTimeout))
	conn.SetPongHandler(func(string) error {
		return conn.SetReadDeadline(time.Now().Add(pongTimeout))
	})

	sseURL := fmt.Sprintf("%s/events/stream/%s", h.brokerURL, topic)
	req, err := http.NewRequestWithContext(r.Context(), http.MethodGet, sseURL, nil)
	if err != nil {
		writeCloseFrame(conn, websocket.CloseInternalServerErr, "broker connect error")
		return
	}
	req.Header.Set("Accept", "text/event-stream")
	req.Header.Set("Cache-Control", "no-cache")

	resp, err := h.httpClient.Do(req)
	if err != nil {
		writeCloseFrame(conn, websocket.CloseInternalServerErr, "broker unavailable")
		return
	}

	var closeOnce sync.Once
	closeBody := func() { closeOnce.Do(func() { resp.Body.Close() }) }
	defer closeBody()

	outbound := make(chan []byte, outboundQueue)
	done := make(chan struct{})
	var doneOnce sync.Once
	closeDone := func() { doneOnce.Do(func() { close(done); closeBody() }) }

	// reader: detect client disconnect, refresh deadlines from pongs.
	go func() {
		defer closeDone()
		for {
			if _, _, err := conn.ReadMessage(); err != nil {
				return
			}
		}
	}()

	// writer: own all writes to conn — gorilla/websocket forbids concurrent
	// writes. Handles outbound payloads + periodic pings.
	go func() {
		ticker := time.NewTicker(pingInterval)
		defer ticker.Stop()
		defer closeDone()

		for {
			select {
			case <-done:
				return
			case payload, ok := <-outbound:
				if !ok {
					return
				}
				_ = conn.SetWriteDeadline(time.Now().Add(writeDeadline))
				if err := conn.WriteMessage(websocket.TextMessage, payload); err != nil {
					return
				}
			case <-ticker.C:
				_ = conn.SetWriteDeadline(time.Now().Add(writeDeadline))
				if err := conn.WriteMessage(websocket.PingMessage, nil); err != nil {
					return
				}
			}
		}
	}()

	// pump (main goroutine): read SSE, enqueue onto outbound.
	scanner := bufio.NewScanner(resp.Body)
	scanner.Buffer(make([]byte, scannerInitBuf), scannerMaxBuf)

	for scanner.Scan() {
		select {
		case <-done:
			return
		default:
		}
		line := scanner.Bytes()
		if !hasPrefix(line, "data: ") {
			continue
		}
		payload := append([]byte(nil), line[len("data: "):]...) // copy: scanner reuses buffer

		select {
		case outbound <- payload:
			// queued
		default:
			// Slow client — outbound chan full. Drop the connection rather
			// than block the SSE reader (which would back up the broker).
			closeDone()
			return
		}
	}
}

func writeCloseFrame(conn *websocket.Conn, code int, reason string) {
	_ = conn.SetWriteDeadline(time.Now().Add(writeDeadline))
	_ = conn.WriteMessage(websocket.CloseMessage, websocket.FormatCloseMessage(code, reason))
}

// hasPrefix is a zero-alloc bytes prefix check.
func hasPrefix(b []byte, prefix string) bool {
	if len(b) < len(prefix) {
		return false
	}
	for i := 0; i < len(prefix); i++ {
		if b[i] != prefix[i] {
			return false
		}
	}
	return true
}
