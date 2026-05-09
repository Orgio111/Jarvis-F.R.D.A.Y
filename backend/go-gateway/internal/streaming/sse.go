package streaming

import (
	"context"
	"encoding/json"
	"fmt"
	"net/http"
	"time"
)

// SSEWriter wraps an http.ResponseWriter to emit Server-Sent Events.
type SSEWriter struct {
	w       http.ResponseWriter
	flusher http.Flusher
}

// NewSSEWriter prepares the response headers for SSE and returns an SSEWriter.
// Returns nil if the ResponseWriter does not support flushing.
func NewSSEWriter(w http.ResponseWriter) *SSEWriter {
	flusher, ok := w.(http.Flusher)
	if !ok {
		return nil
	}

	w.Header().Set("Content-Type", "text/event-stream")
	w.Header().Set("Cache-Control", "no-cache")
	w.Header().Set("Connection", "keep-alive")
	w.Header().Set("X-Accel-Buffering", "no") // disable nginx buffering
	w.WriteHeader(http.StatusOK)
	flusher.Flush()

	return &SSEWriter{w: w, flusher: flusher}
}

// WriteEvent encodes v as JSON and writes a named SSE event.
func (s *SSEWriter) WriteEvent(eventType string, v any) error {
	data, err := json.Marshal(v)
	if err != nil {
		return fmt.Errorf("marshal SSE event: %w", err)
	}

	_, err = fmt.Fprintf(s.w, "event: %s\ndata: %s\n\n", eventType, data)
	if err != nil {
		return err
	}
	s.flusher.Flush()
	return nil
}

// WriteRaw writes a pre-serialised JSON data line.
func (s *SSEWriter) WriteRaw(eventType string, data []byte) error {
	_, err := fmt.Fprintf(s.w, "event: %s\ndata: %s\n\n", eventType, data)
	if err != nil {
		return err
	}
	s.flusher.Flush()
	return nil
}

// WriteHeartbeat sends a comment-only keep-alive line.
func (s *SSEWriter) WriteHeartbeat() {
	fmt.Fprintf(s.w, ": heartbeat %s\n\n", time.Now().UTC().Format(time.RFC3339))
	s.flusher.Flush()
}

// WriteDone sends a "done" event to signal stream completion.
func (s *SSEWriter) WriteDone() {
	fmt.Fprintf(s.w, "event: done\ndata: {}\n\n")
	s.flusher.Flush()
}

// HeartbeatLoop runs a keep-alive heartbeat goroutine.
// It stops when ctx is cancelled.
func HeartbeatLoop(ctx context.Context, sse *SSEWriter, interval time.Duration) {
	ticker := time.NewTicker(interval)
	defer ticker.Stop()
	for {
		select {
		case <-ctx.Done():
			return
		case <-ticker.C:
			sse.WriteHeartbeat()
		}
	}
}
