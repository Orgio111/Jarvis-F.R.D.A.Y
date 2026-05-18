package contracts

import (
	"encoding/json"
	"net/http"
	"time"
)

// ─── Canonical Response Envelopes ─────────────────────────────────────────────

type successEnvelope struct {
	Ok            bool            `json:"ok"`
	Data          any             `json:"data"`
	CorrelationID string          `json:"correlationId"`
	Timestamp     string          `json:"timestamp"`
}

type errorDetail struct {
	Code    string         `json:"code"`
	Message string         `json:"message"`
	Details map[string]any `json:"details,omitempty"`
}

type errorEnvelope struct {
	Ok            bool        `json:"ok"`
	Error         errorDetail `json:"error"`
	CorrelationID string      `json:"correlationId"`
	Timestamp     string      `json:"timestamp"`
}

// ─── BackendEvent — canonical SSE / WebSocket event ───────────────────────────

type BackendEvent struct {
	ID            string          `json:"id"`
	Type          string          `json:"type"`
	Version       string          `json:"version"`
	Timestamp     string          `json:"timestamp"`
	CorrelationID string          `json:"correlationId"`
	RequestID     *string         `json:"requestId"`
	SessionID     *string         `json:"sessionId"`
	Source        string          `json:"source"`
	Payload       json.RawMessage `json:"payload"`
}

// ─── Response helpers ─────────────────────────────────────────────────────────

func WriteSuccess(w http.ResponseWriter, correlationID string, data any) {
	env := successEnvelope{
		Ok:            true,
		Data:          data,
		CorrelationID: correlationID,
		Timestamp:     now(),
	}
	writeJSON(w, http.StatusOK, env)
}

func WriteError(w http.ResponseWriter, correlationID string, status int, code, message string, details map[string]any) {
	env := errorEnvelope{
		Ok: false,
		Error: errorDetail{
			Code:    code,
			Message: message,
			Details: details,
		},
		CorrelationID: correlationID,
		Timestamp:     now(),
	}
	writeJSON(w, status, env)
}

func WriteBadRequest(w http.ResponseWriter, correlationID, code, message string) {
	WriteError(w, correlationID, http.StatusBadRequest, code, message, nil)
}

func WriteNotFound(w http.ResponseWriter, correlationID string) {
	WriteError(w, correlationID, http.StatusNotFound, "not_found", "The requested resource was not found.", nil)
}

func WriteServiceUnavailable(w http.ResponseWriter, correlationID, service string) {
	WriteError(w, correlationID, http.StatusServiceUnavailable, "service_unavailable",
		service+" is not available", map[string]any{"service": service})
}

// WriteCircuitOpen writes a 503 with code "circuit_open" — use when the
// circuit breaker has tripped for a downstream service.
func WriteCircuitOpen(w http.ResponseWriter, correlationID, service string) {
	WriteError(w, correlationID, http.StatusServiceUnavailable, "circuit_open",
		service+" circuit breaker is open — too many recent failures, try again later",
		map[string]any{"service": service})
}

func WriteInternalError(w http.ResponseWriter, correlationID string) {
	WriteError(w, correlationID, http.StatusInternalServerError, "internal_error", "An internal error occurred.", nil)
}

func writeJSON(w http.ResponseWriter, status int, v any) {
	w.Header().Set("Content-Type", "application/json; charset=utf-8")
	w.Header().Set("X-Content-Type-Options", "nosniff")
	w.WriteHeader(status)
	_ = json.NewEncoder(w).Encode(v)
}

func now() string {
	return time.Now().UTC().Format(time.RFC3339Nano)
}
