package middleware

import (
	"context"
	"net/http"

	"github.com/google/uuid"
)

type contextKey string

const (
	CorrelationIDKey contextKey = "correlationId"
	SessionIDKey     contextKey = "sessionId"
	ClientVersionKey contextKey = "clientVersion"
	RequestIDKey     contextKey = "requestId"
)

// Correlation injects or propagates X-Request-ID and X-Correlation-ID headers.
// A new UUID is generated for every request. The correlation ID is also injected
// into the response so the client can match it to log entries.
func Correlation(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		requestID := r.Header.Get("X-Request-ID")
		if requestID == "" {
			requestID = uuid.New().String()
		}

		correlationID := r.Header.Get("X-Correlation-ID")
		if correlationID == "" {
			correlationID = requestID
		}

		w.Header().Set("X-Request-ID", requestID)
		w.Header().Set("X-Correlation-ID", correlationID)

		ctx := context.WithValue(r.Context(), RequestIDKey, requestID)
		ctx = context.WithValue(ctx, CorrelationIDKey, correlationID)

		next.ServeHTTP(w, r.WithContext(ctx))
	})
}

// GetCorrelationID retrieves the correlation ID from context.
func GetCorrelationID(r *http.Request) string {
	if v, ok := r.Context().Value(CorrelationIDKey).(string); ok {
		return v
	}
	return uuid.New().String()
}

// GetRequestID retrieves the request ID from context.
func GetRequestID(r *http.Request) string {
	if v, ok := r.Context().Value(RequestIDKey).(string); ok {
		return v
	}
	return uuid.New().String()
}

// GetSessionID retrieves the session ID from context.
func GetSessionID(r *http.Request) string {
	if v, ok := r.Context().Value(SessionIDKey).(string); ok {
		return v
	}
	return ""
}

// GetClientVersion retrieves the client version from context.
func GetClientVersion(r *http.Request) string {
	if v, ok := r.Context().Value(ClientVersionKey).(string); ok {
		return v
	}
	return ""
}
